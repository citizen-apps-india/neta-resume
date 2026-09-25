"""ECI Files — load reviewed data files -> eci_file_entry/person/citation.

The input is data/eci_files/entries/*.json, hand-researched and fact-checked (BRIEF.md format,
each file adding an `area`, each entry adding a `check` field). Nothing is fetched here: this
pipeline only reads files already in the repo. Idempotent by full replace — the data files are the
truth, so an entry removed from the files disappears on the next load. Each citation gets a
source_ref filed under the source code matching that citation's tier (db/seeds/sources.sql:
eci_files_primary/research/press).
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

_TIER_TO_SOURCE_CODE = {1: "eci_files_primary", 2: "eci_files_research", 3: "eci_files_press"}
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(name: str) -> str:
    slug = _SLUG_RE.sub("-", name.strip().lower()).strip("-")
    return slug or "unknown"


class EntryCitation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    url: str = Field(min_length=1)
    publisher: str | None = None
    title: str | None = None
    published: date_type | None = None
    tier: int = Field(ge=1, le=3)
    archive_url: str | None = None
    quote: str | None = None

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


def _profile_name(entry: Entry) -> str:
    return entry.people[0] if entry.people else entry.title


def _replace_all(loaded: list[LoadedEntry]) -> None:
    with session_scope() as s:
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
                         notes, check_status)
                    VALUES
                        (:id, :area, :kind, :date, :date_precision, :title, :summary, :status,
                         :attributed_to, CAST(:topics AS text[]), CAST(:states AS text[]),
                         CAST(:figures AS jsonb), CAST(:details AS jsonb), :response_to,
                         :notes, :check_status)
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
                },
            )

        person_names: set[str] = set()
        profile_entry_by_name: dict[str, str] = {}
        for _, entry in loaded:
            person_names.update(entry.people)
            if entry.kind == "person":
                name = _profile_name(entry)
                person_names.add(name)
                profile_entry_by_name[name] = entry.id

        for name in sorted(person_names):
            s.execute(
                text("""
                    INSERT INTO eci_file_person (slug, name, profile_entry_id)
                    VALUES (:slug, :name, :profile_entry_id)
                """),
                {
                    "slug": _slugify(name),
                    "name": name,
                    "profile_entry_id": profile_entry_by_name.get(name),
                },
            )

        for _, entry in loaded:
            for name in dict.fromkeys(entry.people):
                s.execute(
                    text("""
                        INSERT INTO eci_file_entry_person (entry_id, person_slug)
                        VALUES (:entry_id, :person_slug)
                    """),
                    {"entry_id": entry.id, "person_slug": _slugify(name)},
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


def run(path: str | Path | None = None) -> None:
    src = Path(path) if path is not None else DEFAULT_PATH
    loaded, errors = _load_entries(src)
    if errors:
        raise EciFilesValidationError(errors)

    _replace_all(loaded)

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
