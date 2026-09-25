"""ECI Files — load reviewed data files -> eci_file_entry/person/citation (+ lanes, state figures,
headline).

The input is data/eci_files/entries/*.json, hand-researched and fact-checked (BRIEF.md format,
each file adding an `area`, each entry adding a `check` field). Nothing is fetched here: this
pipeline only reads files already in the repo. Idempotent by full replace — the data files are the
truth, so an entry removed from the files disappears on the next load. Each citation gets a
source_ref filed under the source code matching that citation's tier (db/seeds/sources.sql:
eci_files_primary/research/press).

Two more, optional, curated files feed the same full replace: `data/eci_files/states.json` (per-state
SIR stage figures -> eci_file_state_stage) and `data/eci_files/headline.json` (the front page's four
headline stats -> eci_file_headline, plus the key-moments entry ids -> eci_file_key_moment). Both are
loaded only when `run()` is called with no explicit `path` (the real, production entries directory) —
a caller that points `path` at a fixture or test directory gets neither, so tests never depend on the
real files. Either can also be pointed at explicitly via `states_path`/`headline_path`.
"""

from __future__ import annotations

import json
import re
from datetime import date as date_type
from pathlib import Path
from typing import Any, NamedTuple

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy import text

from neta_core.db.engine import session_scope
from neta_core.provenance import record_source_ref

REPO_ROOT = Path(__file__).parents[4]
DEFAULT_PATH = REPO_ROOT / "data" / "eci_files" / "entries"
DEFAULT_STATES_PATH = REPO_ROOT / "data" / "eci_files" / "states.json"
DEFAULT_HEADLINE_PATH = REPO_ROOT / "data" / "eci_files" / "headline.json"

_TIER_TO_SOURCE_CODE = {1: "eci_files_primary", 2: "eci_files_research", 3: "eci_files_press"}
_SLUG_RE = re.compile(r"[^a-z0-9]+")
_PROFILE_AREAS = frozenset({"commissioners", "officials"})
_LANES = ("responses", "claims", "courts", "inside", "commission")
_STAGES = ("before", "draft", "final", "appeals_filed", "appeals_pending", "restored")


def _slugify(name: str) -> str:
    slug = _SLUG_RE.sub("-", name.strip().lower()).strip("-")
    return slug or "unknown"


def _partial_date(v: Any) -> Any:
    """'2026-07' -> 2026-07-01 and '2019' -> 2019-01-01; date_precision records how much was known."""
    if isinstance(v, str) and re.fullmatch(r"\d{4}(-\d{2})?", v):
        return f"{v}-01-01" if len(v) == 4 else f"{v}-01"
    return v


class EntryCitation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    url: str = Field(min_length=1)
    publisher: str | None = None
    title: str | None = None
    published: date_type | None = None
    tier: int = Field(ge=1, le=3)
    archive_url: str | None = None
    quote: str | None = None

    _published = field_validator("published", mode="before")(lambda v: _partial_date(v))

    @field_validator("quote")
    @classmethod
    def _quote_is_short(cls, v: str | None) -> str | None:
        if v is not None and len(v.split()) > 15:
            raise ValueError("quote must be 15 words or fewer")
        return v


class Entry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1)
    kind: str = Field(pattern=r"^(event|person|rule|figure|case|statement)$")
    date: date_type | None = None
    date_precision: str = Field(pattern=r"^(day|month|year)$")
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    status: str = Field(pattern=r"^(documented|reported|claim|response)$")
    attributed_to: str | None = None
    people: list[str] = Field(default_factory=list)
    states: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    figures: list[dict[str, Any]] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
    sources: list[EntryCitation] = Field(min_length=1)
    response_to: str | None = None
    notes: str | None = None
    check: str = Field(pattern=r"^(checked|unchecked)$")
    exclude: bool = False

    _date = field_validator("date", mode="before")(lambda v: _partial_date(v))


def _derive_lane(entry: Entry) -> str:
    """Deterministic lane assignment; the first matching rule wins (redesign spec 1a)."""
    if entry.status == "response":
        return "responses"
    if entry.status == "claim":
        return "claims"
    if "courts" in entry.topics or entry.kind == "case":
        return "courts"
    if "dissent" in entry.topics:
        return "inside"
    return "commission"


class EciStateStage(BaseModel):
    """One state's figure at one SIR stage, flattened from states.json's per-state `stages` list."""

    model_config = ConfigDict(extra="ignore")

    state: str = Field(min_length=1)
    stage: str = Field(pattern=r"^(before|draft|final|appeals_filed|appeals_pending|restored)$")
    electors: int = Field(ge=0)
    as_of: date_type | None = None
    computed: bool = False
    source_entry: str = Field(min_length=1)
    url: str = Field(min_length=1)
    tier: int = Field(ge=1, le=3)

    _as_of = field_validator("as_of", mode="before")(lambda v: _partial_date(v))


class HeadlineStat(BaseModel):
    model_config = ConfigDict(extra="ignore")

    value: str = Field(min_length=1)
    label: str = Field(min_length=1)
    source_label: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    entry_id: str = Field(min_length=1)


class HeadlineFile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    headline: list[HeadlineStat] = Field(default_factory=list)
    key_moments: list[str] = Field(default_factory=list)


class LoadedEntry(NamedTuple):
    area: str
    entry: Entry


class EciFilesValidationError(Exception):
    """One or more entries failed validation; every error is reported at once."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("\n".join(errors))


def _load_entries(path: Path) -> tuple[list[LoadedEntry], list[str]]:
    loaded: list[LoadedEntry] = []
    errors: list[str] = []
    seen_ids: dict[str, Path] = {}

    for file in sorted(path.glob("*.json")):
        try:
            payload = json.loads(file.read_text())
        except json.JSONDecodeError as e:
            errors.append(f"{file.name}: invalid JSON: {e}")
            continue
        area = payload.get("area")
        if not area:
            errors.append(f"{file.name}: missing required 'area'")
            continue
        for i, raw in enumerate(payload.get("entries", [])):
            if raw.get("exclude"):
                continue
            try:
                entry = Entry.model_validate(raw)
            except ValidationError as e:
                label = raw.get("id", f"entries[{i}]")
                errors.append(f"{file.name}: {label}: {e}")
                continue
            if entry.id in seen_ids:
                errors.append(
                    f"{file.name}: duplicate entry id {entry.id!r} (first seen in "
                    f"{seen_ids[entry.id].name})"
                )
                continue
            seen_ids[entry.id] = file
            loaded.append(LoadedEntry(area=area, entry=entry))

    return loaded, errors


def _load_state_stages(path: Path | None) -> tuple[list[EciStateStage], list[str]]:
    """states.json is optional: `[]` with no errors when absent, per "if the file exists"."""
    if path is None or not path.exists():
        return [], []
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return [], [f"{path.name}: invalid JSON: {e}"]

    stages: list[EciStateStage] = []
    errors: list[str] = []
    for i, raw_state in enumerate(payload.get("states", [])):
        state_name = raw_state.get("state") or f"states[{i}]"
        for j, raw_stage in enumerate(raw_state.get("stages", [])):
            try:
                stages.append(EciStateStage.model_validate({**raw_stage, "state": raw_state.get("state")}))
            except ValidationError as e:
                errors.append(f"{path.name}: {state_name}.stages[{j}]: {e}")
    return stages, errors


def _load_headline(path: Path | None) -> tuple[HeadlineFile | None, list[str]]:
    """headline.json is optional: `None` with no errors when absent, per "if the file exists"."""
    if path is None or not path.exists():
        return None, []
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return None, [f"{path.name}: invalid JSON: {e}"]
    try:
        return HeadlineFile.model_validate(payload), []
    except ValidationError as e:
        return None, [f"{path.name}: {e}"]


def _profile_name(entry: Entry) -> str:
    """A person entry's subject: its first named person, else the title up to "Name: role"'s colon."""
    return entry.people[0] if entry.people else entry.title.split(":", 1)[0].strip()


def _replace_all(
    loaded: list[LoadedEntry],
    state_stages: list[EciStateStage],
    headline: HeadlineFile | None,
) -> None:
    with session_scope() as s:
        s.execute(text("DELETE FROM eci_file_key_moment"))
        s.execute(text("DELETE FROM eci_file_headline"))
        s.execute(text("DELETE FROM eci_file_state_stage"))
        s.execute(text("DELETE FROM eci_file_citation"))
        s.execute(text("DELETE FROM eci_file_entry_person"))
        s.execute(text("DELETE FROM eci_file_person"))
        s.execute(text("DELETE FROM eci_file_entry"))

        for area, entry in loaded:
            s.execute(
                text("""
                    INSERT INTO eci_file_entry
                        (id, area, kind, date, date_precision, title, summary, status,
                         attributed_to, topics, states, figures, details, response_to,
                         notes, check_status, lane)
                    VALUES
                        (:id, :area, :kind, :date, :date_precision, :title, :summary, :status,
                         :attributed_to, CAST(:topics AS text[]), CAST(:states AS text[]),
                         CAST(:figures AS jsonb), CAST(:details AS jsonb), :response_to,
                         :notes, :check_status, :lane)
                """),
                {
                    "id": entry.id,
                    "area": area,
                    "kind": entry.kind,
                    "date": entry.date,
                    "date_precision": entry.date_precision,
                    "title": entry.title,
                    "summary": entry.summary,
                    "status": entry.status,
                    "attributed_to": entry.attributed_to,
                    "topics": entry.topics,
                    "states": entry.states,
                    "figures": json.dumps(entry.figures),
                    "details": json.dumps(entry.details),
                    "response_to": entry.response_to,
                    "notes": entry.notes,
                    "check_status": entry.check,
                    "lane": _derive_lane(entry),
                },
            )

        # Spellings that slug alike ("P. Pawan", "P Pawan") are one person; a profile's own name wins.
        names_by_slug: dict[str, str] = {}
        profile_by_slug: dict[str, str] = {}
        # Several areas may profile one person; a checked profile from the people areas wins.
        profile_rank: dict[str, tuple[bool, bool]] = {}
        for area, entry in loaded:
            for name in entry.people:
                slug = _slugify(name)
                if len(name) > len(names_by_slug.get(slug, "")):
                    names_by_slug[slug] = name
            if entry.kind == "person":
                name, slug = _profile_name(entry), _slugify(_profile_name(entry))
                rank = (entry.check == "checked", area in _PROFILE_AREAS)
                if slug not in profile_rank or rank > profile_rank[slug]:
                    names_by_slug[slug] = name
                    profile_by_slug[slug] = entry.id
                    profile_rank[slug] = rank

        for slug, name in sorted(names_by_slug.items()):
            s.execute(
                text("""
                    INSERT INTO eci_file_person (slug, name, profile_entry_id)
                    VALUES (:slug, :name, :profile_entry_id)
                """),
                {"slug": slug, "name": name, "profile_entry_id": profile_by_slug.get(slug)},
            )

        for _, entry in loaded:
            for slug in dict.fromkeys(_slugify(name) for name in entry.people):
                s.execute(
                    text("""
                        INSERT INTO eci_file_entry_person (entry_id, person_slug)
                        VALUES (:entry_id, :person_slug)
                    """),
                    {"entry_id": entry.id, "person_slug": slug},
                )

        for _, entry in loaded:
            for position, citation in enumerate(entry.sources, start=1):
                source_ref_id = record_source_ref(
                    s,
                    source_code=_TIER_TO_SOURCE_CODE[citation.tier],
                    native_id=citation.url,
                    native_url=citation.url,
                    raw_name=citation.title,
                )
                s.execute(
                    text("""
                        INSERT INTO eci_file_citation
                            (entry_id, position, source_ref_id, publisher, title, published,
                             tier, archive_url, quote)
                        VALUES
                            (:entry_id, :position, :source_ref_id, :publisher, :title, :published,
                             :tier, :archive_url, :quote)
                    """),
                    {
                        "entry_id": entry.id,
                        "position": position,
                        "source_ref_id": source_ref_id,
                        "publisher": citation.publisher,
                        "title": citation.title,
                        "published": citation.published,
                        "tier": citation.tier,
                        "archive_url": citation.archive_url,
                        "quote": citation.quote,
                    },
                )

        for stage in state_stages:
            s.execute(
                text("""
                    INSERT INTO eci_file_state_stage
                        (state, stage, electors, as_of, computed, source_entry_id, url, tier)
                    VALUES
                        (:state, :stage, :electors, :as_of, :computed, :source_entry_id, :url, :tier)
                """),
                {
                    "state": stage.state,
                    "stage": stage.stage,
                    "electors": stage.electors,
                    "as_of": stage.as_of,
                    "computed": stage.computed,
                    "source_entry_id": stage.source_entry,
                    "url": stage.url,
                    "tier": stage.tier,
                },
            )

        if headline is not None:
            for position, stat in enumerate(headline.headline, start=1):
                s.execute(
                    text("""
                        INSERT INTO eci_file_headline
                            (position, value, label, source_label, source_url, entry_id)
                        VALUES
                            (:position, :value, :label, :source_label, :source_url, :entry_id)
                    """),
                    {"position": position, **stat.model_dump()},
                )
            for position, entry_id in enumerate(headline.key_moments, start=1):
                s.execute(
                    text("""
                        INSERT INTO eci_file_key_moment (position, entry_id)
                        VALUES (:position, :entry_id)
                    """),
                    {"position": position, "entry_id": entry_id},
                )


def run(
    path: str | Path | None = None,
    states_path: str | Path | None = None,
    headline_path: str | Path | None = None,
) -> None:
    using_defaults = path is None
    src = Path(path) if path is not None else DEFAULT_PATH
    loaded, errors = _load_entries(src)

    resolved_states = Path(states_path) if states_path is not None else (
        DEFAULT_STATES_PATH if using_defaults else None
    )
    resolved_headline = Path(headline_path) if headline_path is not None else (
        DEFAULT_HEADLINE_PATH if using_defaults else None
    )
    state_stages, state_errors = _load_state_stages(resolved_states)
    headline, headline_errors = _load_headline(resolved_headline)

    errors = errors + state_errors + headline_errors
    if errors:
        raise EciFilesValidationError(errors)

    _replace_all(loaded, state_stages, headline)

    entries = [entry for _, entry in loaded]
    people = {name for e in entries for name in e.people} | {
        _profile_name(e) for e in entries if e.kind == "person"
    }
    citations = sum(len(e.sources) for e in entries)
    checked = sum(1 for e in entries if e.check == "checked")
    print(
        f"[eci-files] loaded {len(entries)} entries, {len(people)} people, {citations} citations "
        f"({checked} checked, {len(entries) - checked} unchecked)"
    )
    if resolved_states is not None and resolved_states.exists():
        print(f"[eci-files] loaded {len(state_stages)} state stages across "
              f"{len({s.state for s in state_stages})} states")
    if headline is not None:
        print(f"[eci-files] loaded {len(headline.headline)} headline stats, "
              f"{len(headline.key_moments)} key moments")
