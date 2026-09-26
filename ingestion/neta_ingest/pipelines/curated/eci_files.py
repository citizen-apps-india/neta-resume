"""ECI Files — load reviewed data files -> eci_file_entry/person/citation (+ lanes, regions, state
figures, national figures, headline).

The input is data/eci_files/entries/*.json, hand-researched and fact-checked (BRIEF.md format,
each file adding an `area`, each entry adding a `check` field). Nothing is fetched here: this
pipeline only reads files already in the repo. Idempotent by full replace — the data files are the
truth, so an entry removed from the files disappears on the next load. Each citation gets a
source_ref filed under the source code matching that citation's tier (db/seeds/sources.sql:
eci_files_primary/research/press).

Four more curated files feed the same full replace:

- `data/eci_files/regions.json` (36 States/UTs, with aliases for the inconsistent state names used
  in entries and in states.json). It is static reference data and is **always** loaded, from
  `DEFAULT_REGIONS_PATH` unless `regions_path` is given explicitly — even a fixture-pointed run
  gets the real regions.
- `data/eci_files/states.json` (per-region SIR stage figures -> eci_file_state / eci_file_state_stage)
  and `data/eci_files/national.json` (the national totals the record itself carries ->
  eci_file_national_figure) are loaded only when `run()` is called with no explicit `path` (the
  real, production entries directory) — a caller that points `path` at a fixture or test directory
  gets neither, so tests never depend on the real files. Either can also be pointed at explicitly
  via `states_path`/`national_path`.
- `data/eci_files/headline.json` (the front page's four headline stats -> eci_file_headline, plus
  the key-moments entry ids -> eci_file_key_moment) follows the same states_path rule, via
  `headline_path`.
- `data/eci_files/selections.json` (who selected whom, 2019-2025 -> eci_file_selection_regime /
  eci_file_selection / eci_file_selection_person / eci_file_departure) and
  `data/eci_files/people_media.json` (photo credits -> eci_file_person_media) follow the same
  states_path rule too, via `selections_path`/`media_path`. Every entry id either file cites must be
  a loaded entry id, and every person slug it cites must be a slug in the person set built from the
  entries (`_build_people`).

Every state/UT name is canonicalised against `regions.json`'s names and aliases before insert: an
entry's `states` array and each states.json region's `state` field are both resolved to a single
canonical name (an unknown name is a validation error). Every non-computed state-stage value, and
every national figure regardless of `computed`, must equal a `figures[].value` on its cited entry;
this is checked at load time so a record and its source can never quietly drift apart.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date as date_type
from pathlib import Path
from typing import Any, Literal, NamedTuple

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy import text

from neta_core.db.engine import session_scope
from neta_core.provenance import record_source_ref

REPO_ROOT = Path(__file__).parents[4]
DEFAULT_PATH = REPO_ROOT / "data" / "eci_files" / "entries"
DEFAULT_STATES_PATH = REPO_ROOT / "data" / "eci_files" / "states.json"
DEFAULT_HEADLINE_PATH = REPO_ROOT / "data" / "eci_files" / "headline.json"
DEFAULT_REGIONS_PATH = REPO_ROOT / "data" / "eci_files" / "regions.json"
DEFAULT_NATIONAL_PATH = REPO_ROOT / "data" / "eci_files" / "national.json"
DEFAULT_SELECTIONS_PATH = REPO_ROOT / "data" / "eci_files" / "selections.json"
DEFAULT_MEDIA_PATH = REPO_ROOT / "data" / "eci_files" / "people_media.json"
DEFAULT_OBJECTIONS_PATH = REPO_ROOT / "data" / "eci_files" / "objections.json"
DEFAULT_PAIRS_PATH = REPO_ROOT / "data" / "eci_files" / "pairs.json"
DEFAULT_RULE_DIFFS_PATH = REPO_ROOT / "data" / "eci_files" / "rule_diffs.json"
DEFAULT_CASES_PATH = REPO_ROOT / "data" / "eci_files" / "case_orders.json"
DEFAULT_MERGES_PATH = REPO_ROOT / "data" / "eci_files" / "merges.json"

_TIER_TO_SOURCE_CODE = {1: "eci_files_primary", 2: "eci_files_research", 3: "eci_files_press"}
_SLUG_RE = re.compile(r"[^a-z0-9]+")
_PROFILE_AREAS = frozenset({"commissioners", "officials"})
_LANES = ("responses", "claims", "courts", "inside", "commission")
_STAGES = ("before", "draft", "final", "appeals_filed", "appeals_pending", "restored")
_NATIONAL_GROUPS = ("all", "phase_1", "phase_2", "phase_3")
_NATIONAL_MEASURES = ("before", "draft", "final", "left_off", "net_fall")
_REGIME_KEYS = ("convention", "baranwal", "act_2023")
_SELECTION_METHODS = ("executive_appointment", "elevation_of_senior_ec", "selection_committee")
_SELECTION_MEMBER_PARTS = (
    "recommended",
    "proposed",
    "voted_with_majority",
    "dissented",
    "search_chair",
)
_DEPARTURE_HOW = ("resigned", "tenure_ended")
_LICENCE_REVIEW = ("reviewed", "uploader_asserted")

_TEXT_STATUSES = ("verbatim", "quoted in reporting", "paraphrased from reporting")
_TEXT_STATUS_RANK = {status: rank for rank, status in enumerate(_TEXT_STATUSES)}
_PAIR_ITEM_ROLES = ("response", "record", "related", "same")
_CASE_SHORT_STATUSES = ("pending", "disposed", "referred")
_FOLLOWED_BY_PREFIXES = (
    "commissioners-",
    "courts-",
    "elections-2019-2024-",
    "numbers-",
    "officials-",
    "selection-law-",
    "sir-rules-",
    "statements-reporting-",
)
_OBJECTION_REF_RE = re.compile(r"objection (\d+)$")
_PAREN_TOKEN_RE = re.compile(r"\(([^)]+)\)")

_COMMISSION_OFFICE_RE = re.compile(r"^(Chief )?Election Commissioner$")
_STATE_OFFICE_PREFIX = "Chief Electoral Officer"
_SECRETARIAT_RANK_PATTERNS = (
    (re.compile(r"Deputy Election Commissioner"), 0),
    (re.compile(r"Director General"), 1),
    (re.compile(r"Secretary"), 2),
    (re.compile(r"Observer"), 3),
)


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

    def figure_values(self) -> set[Any]:
        return {f["value"] for f in self.figures if "value" in f}


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


class EciRegion(BaseModel):
    model_config = ConfigDict(extra="ignore")

    slug: str = Field(min_length=1)
    name: str = Field(min_length=1)
    code: str = Field(pattern=r"^[A-Z]{2}$")
    kind: str = Field(pattern=r"^(state|ut)$")
    aliases: list[str] = Field(default_factory=list)


class EciStateStage(BaseModel):
    """One state's figure at one SIR stage, nested under `EciState.stages` in states.json."""

    model_config = ConfigDict(extra="ignore")

    stage: str = Field(pattern=r"^(before|draft|final|appeals_filed|appeals_pending|restored)$")
    electors: int = Field(ge=0)
    as_of: date_type | None = None
    computed: bool = False
    approx: bool = False
    note: str | None = None
    source_entry: str = Field(min_length=1)
    url: str = Field(min_length=1)
    tier: int = Field(ge=1, le=3)

    _as_of = field_validator("as_of", mode="before")(lambda v: _partial_date(v))


class EciState(BaseModel):
    """One region's row in states.json: its phase/exercise/notes plus its stage figures."""

    model_config = ConfigDict(extra="ignore")

    state: str = Field(min_length=1)
    phase: int | None = None
    exercise: Literal["sir", "special_revision"] | None = "sir"
    notes: str | None = None
    stages: list[EciStateStage] = Field(default_factory=list)

    @field_validator("phase")
    @classmethod
    def _phase_range(cls, v: int | None) -> int | None:
        if v is not None and not (1 <= v <= 3):
            raise ValueError("phase must be 1, 2, 3 or null")
        return v


class EciNationalFigure(BaseModel):
    model_config = ConfigDict(extra="ignore")

    group: str = Field(pattern=r"^(all|phase_1|phase_2|phase_3)$")
    measure: str = Field(pattern=r"^(before|draft|final|left_off|net_fall)$")
    label: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    electors: int = Field(ge=0)
    as_of: date_type | None = None
    computed: bool = False
    approx: bool = False
    source_entry: str = Field(min_length=1)
    note: str | None = None

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


class SelectionAppointee(BaseModel):
    model_config = ConfigDict(extra="ignore")

    person_slug: str = Field(min_length=1)
    name: str = Field(min_length=1)
    office: str = Field(min_length=1)
    took_charge: date_type | None = None
    replaced: str | None = None

    _took_charge = field_validator("took_charge", mode="before")(lambda v: _partial_date(v))


class SelectionMember(BaseModel):
    model_config = ConfigDict(extra="ignore")

    person_slug: str | None = None
    name: str | None = None
    role: str = Field(min_length=1)
    part: str = Field(pattern="^(" + "|".join(_SELECTION_MEMBER_PARTS) + ")$")
    entry_ids: list[str] = Field(min_length=1)


class SelectionSearch(BaseModel):
    model_config = ConfigDict(extra="ignore")

    by: str = Field(min_length=1)
    chair_slug: str | None = None
    shortlist_size: int | None = None
    shortlist: list[str] | None = None
    shortlist_source: str | None = None
    entry_ids: list[str] = Field(min_length=1)


class SelectionDissent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    person_slug: str = Field(min_length=1)
    name: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    note_public: bool
    status: str = Field(min_length=1)
    entry_ids: list[str] = Field(min_length=1)
    response_entry_ids: list[str] = Field(default_factory=list)


class Selection(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1)
    date: date_type
    date_precision: str = Field(pattern=r"^(day|month|year)$")
    date_meaning: str | None = None
    regime: str = Field(min_length=1)
    method: str = Field(pattern="^(" + "|".join(_SELECTION_METHODS) + ")$")
    appointed: list[SelectionAppointee] = Field(min_length=1)
    members: list[SelectionMember] = Field(default_factory=list)
    search: SelectionSearch | None = None
    dissent: list[SelectionDissent] = Field(default_factory=list)
    entry_ids: list[str] = Field(min_length=1)
    notes: str | None = None

    _date = field_validator("date", mode="before")(lambda v: _partial_date(v))


class SelectionRegime(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    key: str = Field(pattern="^(" + "|".join(_REGIME_KEYS) + ")$")
    label: str = Field(min_length=1)
    from_date: date_type | None = Field(default=None, alias="from")
    to_date: date_type | None = Field(default=None, alias="to")
    rule: str = Field(min_length=1)
    panel: list[str] = Field(default_factory=list)
    entry_ids: list[str] = Field(min_length=1)
    notes: str | None = None

    _from_date = field_validator("from_date", mode="before")(lambda v: _partial_date(v))
    _to_date = field_validator("to_date", mode="before")(lambda v: _partial_date(v))


class Departure(BaseModel):
    model_config = ConfigDict(extra="ignore")

    date: date_type
    person_slug: str = Field(min_length=1)
    office: str = Field(min_length=1)
    how: str = Field(pattern="^(" + "|".join(_DEPARTURE_HOW) + ")$")
    notes: str | None = None
    entry_ids: list[str] = Field(min_length=1)

    _date = field_validator("date", mode="before")(lambda v: _partial_date(v))


class SelectionsFile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    regimes: list[SelectionRegime] = Field(default_factory=list)
    selections: list[Selection] = Field(default_factory=list)
    departures: list[Departure] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class PersonMedia(BaseModel):
    model_config = ConfigDict(extra="ignore")

    slug: str = Field(min_length=1)
    name: str = Field(min_length=1)
    image_url: str = Field(min_length=1)
    source_page: str = Field(min_length=1)
    original_source: str | None = None
    original_publisher: str | None = None
    caption: str | None = None
    photo_date: date_type | None = None
    licence: str = Field(min_length=1)
    licence_url: str = Field(min_length=1)
    licence_review: str = Field(pattern="^(" + "|".join(_LICENCE_REVIEW) + ")$")
    attribution: str = Field(min_length=1)
    self_host: bool = False
    local_path: str | None = None

    _photo_date = field_validator("photo_date", mode="before")(lambda v: _partial_date(v))


class MediaFile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    people: list[PersonMedia] = Field(default_factory=list)


# --- ECI Files phase 5: objections, charge-and-answer pairs, rule diffs, court cases -----------------


class ObjectionEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    n: int = Field(gt=0)
    date: date_type | None = None
    date_precision: str = Field(pattern=r"^(day|month|year)$")
    by: list[str] = Field(min_length=1)
    concerns: str = Field(min_length=1)
    entry_ids: list[str] = Field(min_length=1)
    followed_by: str | None = None
    public: bool

    _date = field_validator("date", mode="before")(lambda v: _partial_date(v))


class ObjectionsFile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    objections: list[ObjectionEntry] = Field(default_factory=list)
    missing: int = Field(ge=0)
    notes: str | None = None
    report_entry_id: str = Field(min_length=1)
    response_entry_id: str = Field(min_length=1)


class PairRelated(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    why: str = Field(min_length=1)


class Pair(BaseModel):
    model_config = ConfigDict(extra="forbid")

    charge_id: str = Field(min_length=1)
    also_recorded_as: list[str] = Field(default_factory=list)
    response_ids: list[str] = Field(default_factory=list)
    record_ids: list[str] = Field(default_factory=list)
    related: list[PairRelated] = Field(default_factory=list)
    note: str | None = None


class UnpairedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_id: str = Field(min_length=1)
    note: str | None = None


class PairsFile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    about: str | None = None
    built_on: str | None = None
    pairs: list[Pair] = Field(default_factory=list)
    unpaired_responses: list[UnpairedResponse] = Field(default_factory=list)


class RuleDiffEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9-]+$")
    rule_entry_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    document: str = Field(min_length=1)
    before_label: str = Field(min_length=1)
    after_label: str = Field(min_length=1)
    before: list[str] = Field(min_length=1)
    after: list[str] = Field(min_length=1)
    before_status: str = Field(pattern="^(" + "|".join(_TEXT_STATUSES) + ")$")
    after_status: str = Field(pattern="^(" + "|".join(_TEXT_STATUSES) + ")$")
    text_status: str = Field(pattern="^(" + "|".join(_TEXT_STATUSES) + ")$")
    excerpt: bool = False
    quoted_lines_before: list[int] = Field(default_factory=list)
    quoted_lines_after: list[int] = Field(default_factory=list)
    source_urls: list[str] = Field(min_length=1)
    note: str | None = None
    related_entry_ids: list[str] = Field(default_factory=list)


class RuleDiffsFile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    about: str | None = None
    built_on: str | None = None
    text_statuses: list[str] = Field(default_factory=list)
    diffs: list[RuleDiffEntry] = Field(default_factory=list)
    gaps: list[dict[str, Any]] = Field(default_factory=list)


class CaseParties(BaseModel):
    model_config = ConfigDict(extra="forbid")

    petitioners: list[str] = Field(default_factory=list)
    respondents: list[str] = Field(default_factory=list)


class CaseItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry_id: str = Field(min_length=1)
    role: str = Field(min_length=1)
    note: str | None = None


class CaseEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str = Field(pattern=r"^[a-z0-9-]+$")
    short_name: str = Field(min_length=1)
    case_entry_id: str = Field(min_length=1)
    court: str = Field(min_length=1)
    short_status: str = Field(pattern="^(" + "|".join(_CASE_SHORT_STATUSES) + ")$")
    status_note: str | None = None
    parties: CaseParties = Field(default_factory=CaseParties)
    items: list[CaseItem] = Field(default_factory=list)


class CaseUnmapped(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry_id: str = Field(min_length=1)
    why: str = Field(min_length=1)


class CasesFile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    about: str | None = None
    built_on: str | None = None
    roles: list[str] = Field(default_factory=list)
    cases: list[CaseEntry] = Field(default_factory=list)
    unmapped: list[CaseUnmapped] = Field(default_factory=list)


class LoadedEntry(NamedTuple):
    area: str
    entry: Entry


class ResolvedStage(NamedTuple):
    region_slug: str
    stage: str
    electors: int
    as_of: date_type | None
    computed: bool
    approx: bool
    note: str | None
    source_entry: str
    url: str
    tier: int


class ResolvedState(NamedTuple):
    region_slug: str
    phase: int | None
    exercise: str | None
    notes: str | None


class ResolvedNationalFigure(NamedTuple):
    position: int
    group: str
    measure: str
    label: str
    scope: str
    electors: int
    as_of: date_type | None
    computed: bool
    approx: bool
    source_entry: str
    note: str | None


class LoadedPayload(NamedTuple):
    entries: list[LoadedEntry]
    regions: list[EciRegion]
    states: list[ResolvedState]
    stages: list[ResolvedStage]
    national: list[ResolvedNationalFigure]
    headline: HeadlineFile | None
    selections: SelectionsFile | None
    media: MediaFile | None
    objections: ObjectionsFile | None = None
    pairs: PairsFile | None = None
    rule_diffs: RuleDiffsFile | None = None
    cases: CasesFile | None = None
    resolved_response_count: int = 0


class PersonGroupInfo(NamedTuple):
    role_group: str
    group_rank: int
    is_current: bool
    first_from: date_type | None
    last_to: date_type | None


class EciFilesValidationError(Exception):
    """One or more entries failed validation; every error is reported at once."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("\n".join(errors))


def _unknown_state_error(file_name: str, label: str, value: str) -> str:
    return f"{file_name}: {label}: unknown state/UT {value!r} (add it to regions.json aliases)"


def _load_regions(path: Path) -> tuple[list[EciRegion], list[str]]:
    if not path.exists():
        return [], [f"{path.name}: file not found"]
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return [], [f"{path.name}: invalid JSON: {e}"]

    regions: list[EciRegion] = []
    errors: list[str] = []
    for i, raw in enumerate(payload.get("regions", [])):
        try:
            regions.append(EciRegion.model_validate(raw))
        except ValidationError as e:
            label = raw.get("slug", f"regions[{i}]")
            errors.append(f"{path.name}: {label}: {e}")

    if len(regions) != 36:
        errors.append(f"{path.name}: expected 36 regions, found {len(regions)}")

    seen_slugs: set[str] = set()
    seen_codes: set[str] = set()
    seen_names_and_aliases: dict[str, str] = {}
    for r in regions:
        if r.slug in seen_slugs:
            errors.append(f"{path.name}: duplicate slug {r.slug!r}")
        seen_slugs.add(r.slug)

        if r.code in seen_codes:
            errors.append(f"{path.name}: duplicate code {r.code!r}")
        seen_codes.add(r.code)

        for key in (r.name, *r.aliases):
            ck = key.casefold()
            if ck in seen_names_and_aliases:
                errors.append(f"{path.name}: duplicate name/alias {key!r}")
            seen_names_and_aliases[ck] = r.slug

        expected_slug = _slugify(r.name)
        if r.slug != expected_slug:
            errors.append(
                f"{path.name}: {r.name}: slug {r.slug!r} does not equal _slugify(name) {expected_slug!r}"
            )

    return regions, errors


def _region_index(regions: list[EciRegion]) -> dict[str, EciRegion]:
    index: dict[str, EciRegion] = {}
    for r in regions:
        index[r.name.casefold()] = r
        for alias in r.aliases:
            index[alias.casefold()] = r
    return index


def _load_entries(
    path: Path, region_index: dict[str, EciRegion]
) -> tuple[list[LoadedEntry], list[str]]:
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

            canonical_states: list[str] = []
            for raw_state in entry.states:
                region = region_index.get(raw_state.casefold())
                if region is None:
                    errors.append(_unknown_state_error(file.name, entry.id, raw_state))
                    continue
                if region.name not in canonical_states:
                    canonical_states.append(region.name)
            entry.states = canonical_states

            seen_ids[entry.id] = file
            loaded.append(LoadedEntry(area=area, entry=entry))

    return loaded, errors


def _load_states(
    path: Path | None, region_index: dict[str, EciRegion], entry_figures: dict[str, set[Any]]
) -> tuple[list[ResolvedState], list[ResolvedStage], list[str]]:
    """states.json is optional: `[]`/`[]` with no errors when absent, per "if the file exists"."""
    if path is None or not path.exists():
        return [], [], []
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return [], [], [f"{path.name}: invalid JSON: {e}"]

    states: list[ResolvedState] = []
    stages: list[ResolvedStage] = []
    errors: list[str] = []
    seen_slugs: set[str] = set()

    for i, raw_state in enumerate(payload.get("states", [])):
        raw_name = raw_state.get("state") or f"states[{i}]"
        try:
            parsed = EciState.model_validate(raw_state)
        except ValidationError as e:
            errors.append(f"{path.name}: {raw_name}: {e}")
            continue

        region = region_index.get(parsed.state.casefold())
        if region is None:
            errors.append(_unknown_state_error(path.name, parsed.state, parsed.state))
            continue

        if region.slug in seen_slugs:
            errors.append(f"{path.name}: {region.name}: region appears twice")
            continue
        seen_slugs.add(region.slug)

        states.append(
            ResolvedState(
                region_slug=region.slug,
                phase=parsed.phase,
                exercise=parsed.exercise,
                notes=parsed.notes,
            )
        )

        seen_stage_types: set[str] = set()
        for stage in parsed.stages:
            if stage.stage in seen_stage_types:
                errors.append(f"{path.name}: {region.name}: duplicate stage {stage.stage!r}")
                continue
            seen_stage_types.add(stage.stage)

            if stage.source_entry not in entry_figures:
                errors.append(
                    f"{path.name}: {region.name}.{stage.stage}: source_entry "
                    f"{stage.source_entry!r} is not a loaded entry id"
                )
            elif not stage.computed and stage.electors not in entry_figures[stage.source_entry]:
                errors.append(
                    f"{path.name}: {region.name}.{stage.stage}: electors {stage.electors} is not "
                    f"a figures[].value of entry {stage.source_entry!r}"
                )

            stages.append(
                ResolvedStage(
                    region_slug=region.slug,
                    stage=stage.stage,
                    electors=stage.electors,
                    as_of=stage.as_of,
                    computed=stage.computed,
                    approx=stage.approx,
                    note=stage.note,
                    source_entry=stage.source_entry,
                    url=stage.url,
                    tier=stage.tier,
                )
            )

    return states, stages, errors


def _load_national(
    path: Path | None, entry_figures: dict[str, set[Any]]
) -> tuple[list[ResolvedNationalFigure], list[str]]:
    """national.json follows the states_path rule: `[]` with no errors when absent."""
    if path is None or not path.exists():
        return [], []
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return [], [f"{path.name}: invalid JSON: {e}"]

    figures: list[ResolvedNationalFigure] = []
    errors: list[str] = []
    for i, raw in enumerate(payload.get("figures", [])):
        label = f"figures[{i}]"
        try:
            parsed = EciNationalFigure.model_validate(raw)
        except ValidationError as e:
            errors.append(f"{path.name}: {label}: {e}")
            continue

        if parsed.source_entry not in entry_figures:
            errors.append(
                f"{path.name}: {parsed.group}/{parsed.measure}: source_entry "
                f"{parsed.source_entry!r} is not a loaded entry id"
            )
        elif parsed.electors not in entry_figures[parsed.source_entry]:
            errors.append(
                f"{path.name}: {parsed.group}/{parsed.measure}: electors {parsed.electors} is not "
                f"a figures[].value of entry {parsed.source_entry!r}"
            )

        figures.append(
            ResolvedNationalFigure(
                position=i + 1,
                group=parsed.group,
                measure=parsed.measure,
                label=parsed.label,
                scope=parsed.scope,
                electors=parsed.electors,
                as_of=parsed.as_of,
                computed=parsed.computed,
                approx=parsed.approx,
                source_entry=parsed.source_entry,
                note=parsed.note,
            )
        )

    return figures, errors


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


def _build_people(
    loaded: list[LoadedEntry],
) -> tuple[dict[str, str], dict[str, str], dict[str, dict]]:
    """Every person slug named anywhere (`names_by_slug`), the checked profile entry that wins each
    slug if any (`profile_by_slug`), and that profile's `details` (`profile_details`). Spellings that
    slug alike ("P. Pawan", "P Pawan") are one person; a checked profile from the people areas wins
    over an unchecked one or one from another area."""
    names_by_slug: dict[str, str] = {}
    profile_by_slug: dict[str, str] = {}
    profile_rank: dict[str, tuple[bool, bool]] = {}
    profile_details: dict[str, dict] = {}
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
                profile_details[slug] = entry.details
    return names_by_slug, profile_by_slug, profile_details


def _parse_tenure_date(v: Any) -> date_type | None:
    if v is None:
        return None
    parsed = _partial_date(v)
    return date_type.fromisoformat(parsed) if isinstance(parsed, str) else None


def _tenure_rows(details: dict) -> list[tuple[date_type | None, date_type | None, str]]:
    return [
        (_parse_tenure_date(t.get("from")), _parse_tenure_date(t.get("to")), t.get("office") or "")
        for t in details.get("tenure") or []
    ]


def _role_group(details: dict) -> str:
    """Section 1.4, first matching rule: `commission` if any tenure office is exactly "Election
    Commissioner" or "Chief Election Commissioner", `state` if any starts with "Chief Electoral
    Officer", else `secretariat` (a profiled person who matched neither)."""
    offices = [office for _, _, office in _tenure_rows(details)]
    if any(_COMMISSION_OFFICE_RE.fullmatch(o) for o in offices):
        return "commission"
    if any(o.startswith(_STATE_OFFICE_PREFIX) for o in offices):
        return "state"
    return "secretariat"


def _is_current(tenure_rows: list[tuple[date_type | None, date_type | None, str]]) -> bool:
    return any(frm is not None and to is None for frm, to, _ in tenure_rows)


def _tenure_bounds(
    tenure_rows: list[tuple[date_type | None, date_type | None, str]],
) -> tuple[date_type | None, date_type | None]:
    firsts = [frm for frm, _, _ in tenure_rows if frm is not None]
    tos = [to for _, to, _ in tenure_rows if to is not None]
    return (min(firsts) if firsts else None, max(tos) if tos else None)


def _office_rank(office: str) -> int:
    for pattern, rank in _SECRETARIAT_RANK_PATTERNS:
        if pattern.search(office):
            return rank
    return 4


def _date_desc_key(d: date_type | None) -> tuple[int, int]:
    """Ascending sort key that puts the latest date first and a null date last."""
    return (1, 0) if d is None else (0, -d.toordinal())


def _date_asc_key(d: date_type | None) -> tuple[int, int]:
    """Ascending sort key that puts the earliest date first and a null date last."""
    return (1, 0) if d is None else (0, d.toordinal())


def _group_sort_key(group: str, name: str, details: dict) -> tuple:
    """Order within group, section 1.4: chronological for the Commission, by state then serving
    then start date for state officers, by office seniority then serving then start date for the
    secretariat."""
    rows = _tenure_rows(details)
    current = _is_current(rows)
    first_from, _ = _tenure_bounds(rows)
    if group == "commission":
        return (_date_asc_key(first_from), name)
    if group == "state":
        state_rows = [r for r in rows if r[2].startswith(_STATE_OFFICE_PREFIX)]
        frm, _, office = state_rows[-1] if state_rows else (None, None, "")
        state_name = office[len(_STATE_OFFICE_PREFIX) :].lstrip(", ").strip()
        return (state_name, 0 if current else 1, _date_desc_key(frm))
    frm, _, office = rows[-1] if rows else (None, None, "")
    return (_office_rank(office), 0 if current else 1, _date_desc_key(frm), name)


def _build_person_groups(
    names_by_slug: dict[str, str],
    profile_by_slug: dict[str, str],
    profile_details: dict[str, dict],
) -> dict[str, PersonGroupInfo]:
    """Every person slug's group, its rank within that group, and the tenure summary columns
    (`is_current`, `first_from`, `last_to`) written onto `eci_file_person`."""
    by_group: dict[str, list[str]] = defaultdict(list)
    for slug in profile_by_slug:
        by_group[_role_group(profile_details[slug])].append(slug)

    result: dict[str, PersonGroupInfo] = {}
    for group, slugs in by_group.items():
        ordered = sorted(
            slugs, key=lambda s: _group_sort_key(group, names_by_slug[s], profile_details[s])
        )
        for rank, slug in enumerate(ordered):
            rows = _tenure_rows(profile_details[slug])
            first_from, last_to = _tenure_bounds(rows)
            result[slug] = PersonGroupInfo(group, rank, _is_current(rows), first_from, last_to)

    named_slugs = sorted(s for s in names_by_slug if s not in profile_by_slug)
    for rank, slug in enumerate(named_slugs):
        result[slug] = PersonGroupInfo("named", rank, False, None, None)
    return result


def _load_selections(
    path: Path | None, entry_ids: set[str], person_slugs: set[str]
) -> tuple[SelectionsFile | None, list[str]]:
    """selections.json is optional, following the states_path rule: `None` with no errors when
    absent. Every entry id cited anywhere in the file must be a loaded (non-excluded) entry id,
    every person_slug/chair_slug/replaced must be a slug in the loaded person set, every selection's
    regime must be a declared regime key, and selection ids must be unique."""
    if path is None or not path.exists():
        return None, []
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return None, [f"{path.name}: invalid JSON: {e}"]
    try:
        parsed = SelectionsFile.model_validate(raw)
    except ValidationError as e:
        return None, [f"{path.name}: {e}"]

    errors: list[str] = []

    def _check_entries(label: str, ids: list[str]) -> None:
        for eid in ids:
            if eid not in entry_ids:
                errors.append(f"{path.name}: {label}: unknown entry id {eid!r}")

    def _check_slug(label: str, slug: str | None) -> None:
        if slug is not None and slug not in person_slugs:
            errors.append(f"{path.name}: {label}: unknown person slug {slug!r}")

    regime_keys = {r.key for r in parsed.regimes}
    for regime in parsed.regimes:
        _check_entries(f"regime {regime.key}", regime.entry_ids)

    seen_ids: set[str] = set()
    for selection in parsed.selections:
        if selection.id in seen_ids:
            errors.append(f"{path.name}: duplicate selection id {selection.id!r}")
        seen_ids.add(selection.id)

        if selection.regime not in regime_keys:
            errors.append(f"{path.name}: {selection.id}: unknown regime {selection.regime!r}")

        _check_entries(selection.id, selection.entry_ids)

        for appointee in selection.appointed:
            _check_slug(f"{selection.id} appointed", appointee.person_slug)
            _check_slug(f"{selection.id} appointed.replaced", appointee.replaced)

        for member in selection.members:
            _check_slug(f"{selection.id} member", member.person_slug)
            _check_entries(f"{selection.id} member", member.entry_ids)

        if selection.search is not None:
            _check_slug(f"{selection.id} search", selection.search.chair_slug)
            _check_entries(f"{selection.id} search", selection.search.entry_ids)

        for dissent in selection.dissent:
            _check_slug(f"{selection.id} dissent", dissent.person_slug)
            _check_entries(f"{selection.id} dissent", dissent.entry_ids)
            _check_entries(f"{selection.id} dissent.response", dissent.response_entry_ids)

    for departure in parsed.departures:
        _check_slug(f"departure {departure.person_slug}", departure.person_slug)
        _check_entries(f"departure {departure.person_slug}", departure.entry_ids)

    if errors:
        return None, errors
    return parsed, []


def _load_media(path: Path | None, person_slugs: set[str]) -> tuple[MediaFile | None, list[str]]:
    """people_media.json is optional, following the states_path rule. Every `slug` must be a slug in
    the loaded person set."""
    if path is None or not path.exists():
        return None, []
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return None, [f"{path.name}: invalid JSON: {e}"]
    try:
        parsed = MediaFile.model_validate(raw)
    except ValidationError as e:
        return None, [f"{path.name}: {e}"]

    errors: list[str] = []
    seen: set[str] = set()
    for person in parsed.people:
        if person.slug in seen:
            errors.append(f"{path.name}: duplicate slug {person.slug!r}")
        seen.add(person.slug)
        if person.slug not in person_slugs:
            errors.append(f"{path.name}: unknown person slug {person.slug!r}")

    if errors:
        return None, errors
    return parsed, []


def _load_merges(path: Path | None) -> tuple[dict[str, str], list[str]]:
    """merges.json's `drop -> keep` map. Optional, following the states_path rule."""
    if path is None or not path.exists():
        return {}, []
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return {}, [f"{path.name}: invalid JSON: {e}"]

    drop_to_keep: dict[str, str] = {}
    for merge in payload.get("merges", []):
        keep = merge.get("keep")
        for drop in merge.get("drop", []):
            drop_to_keep[drop] = keep
    return drop_to_keep, []


def _resolve_response_links(loaded: list[LoadedEntry], drop_to_keep: dict[str, str]) -> int:
    """Rewrites a `response_to` pointing at a merged-away id to the id that replaced it. Returns how
    many links were rewritten."""
    resolved = 0
    for _, entry in loaded:
        if entry.response_to is not None and entry.response_to in drop_to_keep:
            entry.response_to = drop_to_keep[entry.response_to]
            resolved += 1
    return resolved


def _load_objections(
    path: Path | None, entry_ids: set[str], person_slugs: set[str]
) -> tuple[ObjectionsFile | None, list[str]]:
    """objections.json is optional, following the states_path rule."""
    if path is None or not path.exists():
        return None, []
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return None, [f"{path.name}: invalid JSON: {e}"]
    try:
        parsed = ObjectionsFile.model_validate(raw)
    except ValidationError as e:
        return None, [f"{path.name}: {e}"]

    errors: list[str] = []

    def _check_entry(label: str, eid: str) -> None:
        if eid not in entry_ids:
            errors.append(f"{path.name}: {label}: unknown entry id {eid!r}")

    _check_entry("report_entry_id", parsed.report_entry_id)
    _check_entry("response_entry_id", parsed.response_entry_id)

    seen_n: set[int] = set()
    max_n = 0
    for obj in parsed.objections:
        if obj.n in seen_n:
            errors.append(f"{path.name}: objection {obj.n}: duplicate n")
        seen_n.add(obj.n)
        max_n = max(max_n, obj.n)

        for name in obj.by:
            if _slugify(name) not in person_slugs:
                errors.append(f"{path.name}: objection {obj.n}: unknown person {name!r}")

        for eid in obj.entry_ids:
            _check_entry(f"objection {obj.n}", eid)

    expected = set(range(1, max_n + 1))
    if seen_n != expected:
        errors.append(
            f"{path.name}: n values not contiguous from 1 "
            f"(missing {sorted(expected - seen_n)}, unexpected {sorted(seen_n - expected)})"
        )

    for obj in parsed.objections:
        if not obj.followed_by:
            continue
        for token in _PAREN_TOKEN_RE.findall(obj.followed_by):
            m = _OBJECTION_REF_RE.match(token)
            if m:
                if int(m.group(1)) > max_n:
                    errors.append(
                        f"{path.name}: objection {obj.n}: followed_by cites objection "
                        f"{m.group(1)} above the highest n {max_n}"
                    )
            elif token.startswith(_FOLLOWED_BY_PREFIXES):
                _check_entry(f"objection {obj.n} followed_by", token)

    if errors:
        return None, errors
    return parsed, []


def _load_pairs(
    path: Path | None, entry_ids: set[str], entry_status: dict[str, str]
) -> tuple[PairsFile | None, list[str]]:
    """pairs.json is optional, following the states_path rule."""
    if path is None or not path.exists():
        return None, []
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return None, [f"{path.name}: invalid JSON: {e}"]
    try:
        parsed = PairsFile.model_validate(raw)
    except ValidationError as e:
        return None, [f"{path.name}: {e}"]

    errors: list[str] = []

    def _check_entry(label: str, eid: str) -> None:
        if eid not in entry_ids:
            errors.append(f"{path.name}: {label}: unknown entry id {eid!r}")

    seen_charge_ids: set[str] = set()
    also_recorded_ids: set[str] = set()
    all_response_ids: set[str] = set()
    for pair in parsed.pairs:
        if pair.charge_id in seen_charge_ids:
            errors.append(f"{path.name}: duplicate charge_id {pair.charge_id!r}")
        seen_charge_ids.add(pair.charge_id)
        _check_entry(pair.charge_id, pair.charge_id)

        for eid in pair.also_recorded_as:
            _check_entry(f"{pair.charge_id} also_recorded_as", eid)
            also_recorded_ids.add(eid)
        for eid in pair.response_ids:
            _check_entry(f"{pair.charge_id} response_ids", eid)
            if entry_status.get(eid) != "response":
                errors.append(
                    f"{path.name}: {pair.charge_id}: response_ids {eid!r} is not a response entry"
                )
            all_response_ids.add(eid)
        for eid in pair.record_ids:
            _check_entry(f"{pair.charge_id} record_ids", eid)
            if entry_status.get(eid) != "documented":
                errors.append(
                    f"{path.name}: {pair.charge_id}: record_ids {eid!r} is not a documented entry"
                )
        for rel in pair.related:
            _check_entry(f"{pair.charge_id} related", rel.id)

    overlap = seen_charge_ids & also_recorded_ids
    if overlap:
        errors.append(
            f"{path.name}: ids both a charge_id and an also_recorded_as: {sorted(overlap)}"
        )

    for unpaired in parsed.unpaired_responses:
        _check_entry("unpaired_responses", unpaired.response_id)
        if entry_status.get(unpaired.response_id) != "response":
            errors.append(
                f"{path.name}: unpaired_responses {unpaired.response_id!r} is not a response entry"
            )
        if unpaired.response_id in all_response_ids or unpaired.response_id in seen_charge_ids:
            errors.append(
                f"{path.name}: unpaired_responses {unpaired.response_id!r} also appears in a pair"
            )

    if errors:
        return None, errors
    return parsed, []


def _load_rule_diffs(
    path: Path | None, entry_ids: set[str], entry_kind: dict[str, str]
) -> tuple[RuleDiffsFile | None, list[str]]:
    """rule_diffs.json is optional, following the states_path rule."""
    if path is None or not path.exists():
        return None, []
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return None, [f"{path.name}: invalid JSON: {e}"]
    try:
        parsed = RuleDiffsFile.model_validate(raw)
    except ValidationError as e:
        return None, [f"{path.name}: {e}"]

    errors: list[str] = []
    seen_ids: set[str] = set()
    for d in parsed.diffs:
        if d.id in seen_ids:
            errors.append(f"{path.name}: duplicate diff id {d.id!r}")
        seen_ids.add(d.id)

        if d.rule_entry_id not in entry_ids:
            errors.append(f"{path.name}: {d.id}: unknown rule_entry_id {d.rule_entry_id!r}")
        elif entry_kind.get(d.rule_entry_id) != "rule":
            errors.append(
                f"{path.name}: {d.id}: rule_entry_id {d.rule_entry_id!r} is not kind=rule"
            )

        expected = max(d.before_status, d.after_status, key=_TEXT_STATUS_RANK.get)
        if d.text_status != expected:
            errors.append(
                f"{path.name}: {d.id}: text_status {d.text_status!r} is not the weaker of "
                f"before_status {d.before_status!r} and after_status {d.after_status!r} "
                f"({expected!r})"
            )

        for idx in d.quoted_lines_before:
            if not 0 <= idx < len(d.before):
                errors.append(f"{path.name}: {d.id}: quoted_lines_before index {idx} out of range")
        for idx in d.quoted_lines_after:
            if not 0 <= idx < len(d.after):
                errors.append(f"{path.name}: {d.id}: quoted_lines_after index {idx} out of range")

        for eid in d.related_entry_ids:
            if eid not in entry_ids:
                errors.append(f"{path.name}: {d.id}: unknown related_entry_ids id {eid!r}")

    if errors:
        return None, errors
    return parsed, []


def _load_cases(
    path: Path | None, entry_ids: set[str], entry_kind: dict[str, str]
) -> tuple[CasesFile | None, list[str]]:
    """case_orders.json is optional, following the states_path rule."""
    if path is None or not path.exists():
        return None, []
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return None, [f"{path.name}: invalid JSON: {e}"]
    try:
        parsed = CasesFile.model_validate(raw)
    except ValidationError as e:
        return None, [f"{path.name}: {e}"]

    errors: list[str] = []
    seen_slugs: set[str] = set()
    entry_to_case: dict[str, str] = {}
    for case in parsed.cases:
        if case.slug in seen_slugs:
            errors.append(f"{path.name}: duplicate case slug {case.slug!r}")
        seen_slugs.add(case.slug)

        if case.case_entry_id not in entry_ids:
            errors.append(
                f"{path.name}: {case.slug}: unknown case_entry_id {case.case_entry_id!r}"
            )
        elif entry_kind.get(case.case_entry_id) != "case":
            errors.append(
                f"{path.name}: {case.slug}: case_entry_id {case.case_entry_id!r} is not kind=case"
            )

        for item in case.items:
            if item.entry_id not in entry_ids:
                errors.append(
                    f"{path.name}: {case.slug}: unknown item entry id {item.entry_id!r}"
                )
            if item.role not in parsed.roles:
                errors.append(
                    f"{path.name}: {case.slug}: role {item.role!r} not in {parsed.roles}"
                )
            if item.entry_id == case.case_entry_id:
                errors.append(f"{path.name}: {case.slug}: case entry is its own item")
            if item.entry_id in entry_to_case:
                errors.append(
                    f"{path.name}: {item.entry_id!r} is an item of two cases: "
                    f"{entry_to_case[item.entry_id]!r} and {case.slug!r}"
                )
            entry_to_case[item.entry_id] = case.slug

    for u in parsed.unmapped:
        if u.entry_id not in entry_ids:
            errors.append(f"{path.name}: unmapped: unknown entry id {u.entry_id!r}")

    if errors:
        return None, errors
    return parsed, []


def validate_all(
    path: str | Path | None = None,
    states_path: str | Path | None = None,
    headline_path: str | Path | None = None,
    regions_path: str | Path | None = None,
    national_path: str | Path | None = None,
    selections_path: str | Path | None = None,
    media_path: str | Path | None = None,
    objections_path: str | Path | None = None,
    pairs_path: str | Path | None = None,
    rule_diffs_path: str | Path | None = None,
    cases_path: str | Path | None = None,
    merges_path: str | Path | None = None,
) -> tuple[LoadedPayload | None, list[str]]:
    """Parse and cross-validate every ECI Files input, with no database access.

    Returns `(payload, [])` on success or `(None, errors)` with every error collected at once.
    """
    using_defaults = path is None
    src = Path(path) if path is not None else DEFAULT_PATH
    resolved_regions = Path(regions_path) if regions_path is not None else DEFAULT_REGIONS_PATH
    resolved_states = Path(states_path) if states_path is not None else (
        DEFAULT_STATES_PATH if using_defaults else None
    )
    resolved_headline = Path(headline_path) if headline_path is not None else (
        DEFAULT_HEADLINE_PATH if using_defaults else None
    )
    resolved_national = Path(national_path) if national_path is not None else (
        DEFAULT_NATIONAL_PATH if using_defaults else None
    )
    resolved_selections = Path(selections_path) if selections_path is not None else (
        DEFAULT_SELECTIONS_PATH if using_defaults else None
    )
    resolved_media = Path(media_path) if media_path is not None else (
        DEFAULT_MEDIA_PATH if using_defaults else None
    )
    resolved_objections = Path(objections_path) if objections_path is not None else (
        DEFAULT_OBJECTIONS_PATH if using_defaults else None
    )
    resolved_pairs = Path(pairs_path) if pairs_path is not None else (
        DEFAULT_PAIRS_PATH if using_defaults else None
    )
    resolved_rule_diffs = Path(rule_diffs_path) if rule_diffs_path is not None else (
        DEFAULT_RULE_DIFFS_PATH if using_defaults else None
    )
    resolved_cases = Path(cases_path) if cases_path is not None else (
        DEFAULT_CASES_PATH if using_defaults else None
    )
    resolved_merges = Path(merges_path) if merges_path is not None else (
        DEFAULT_MERGES_PATH if using_defaults else None
    )

    regions, region_errors = _load_regions(resolved_regions)
    region_index = _region_index(regions)

    loaded, entry_errors = _load_entries(src, region_index)

    drop_to_keep, merges_errors = _load_merges(resolved_merges)
    resolved_response_count = _resolve_response_links(loaded, drop_to_keep)

    entry_figures = {entry.id: entry.figure_values() for _, entry in loaded}
    entry_ids = set(entry_figures)
    entry_status = {entry.id: entry.status for _, entry in loaded}
    entry_kind = {entry.id: entry.kind for _, entry in loaded}

    response_errors = [
        f"{src.name}: {entry.id}: response_to {entry.response_to!r} is not a loaded entry id"
        for _, entry in loaded
        if entry.response_to is not None and entry.response_to not in entry_ids
    ]

    names_by_slug, _, _ = _build_people(loaded)
    person_slugs = set(names_by_slug)

    states, stages, state_errors = _load_states(resolved_states, region_index, entry_figures)
    national, national_errors = _load_national(resolved_national, entry_figures)
    headline, headline_errors = _load_headline(resolved_headline)
    selections, selections_errors = _load_selections(resolved_selections, entry_ids, person_slugs)
    media, media_errors = _load_media(resolved_media, person_slugs)
    objections, objections_errors = _load_objections(resolved_objections, entry_ids, person_slugs)
    pairs, pairs_errors = _load_pairs(resolved_pairs, entry_ids, entry_status)
    rule_diffs, rule_diffs_errors = _load_rule_diffs(resolved_rule_diffs, entry_ids, entry_kind)
    cases, cases_errors = _load_cases(resolved_cases, entry_ids, entry_kind)

    errors = (
        region_errors
        + entry_errors
        + merges_errors
        + response_errors
        + state_errors
        + national_errors
        + headline_errors
        + selections_errors
        + media_errors
        + objections_errors
        + pairs_errors
        + rule_diffs_errors
        + cases_errors
    )
    if errors:
        return None, errors

    payload = LoadedPayload(
        entries=loaded,
        regions=regions,
        states=states,
        stages=stages,
        national=national,
        headline=headline,
        selections=selections,
        media=media,
        objections=objections,
        pairs=pairs,
        rule_diffs=rule_diffs,
        cases=cases,
        resolved_response_count=resolved_response_count,
    )
    return payload, []


def _replace_all(payload: LoadedPayload) -> None:
    with session_scope() as s:
        s.execute(text("DELETE FROM eci_file_case_item"))
        s.execute(text("DELETE FROM eci_file_case"))
        s.execute(text("DELETE FROM eci_file_rule_diff_entry"))
        s.execute(text("DELETE FROM eci_file_rule_diff"))
        s.execute(text("DELETE FROM eci_file_unpaired_response"))
        s.execute(text("DELETE FROM eci_file_pair_item"))
        s.execute(text("DELETE FROM eci_file_pair"))
        s.execute(text("DELETE FROM eci_file_objection_meta"))
        s.execute(text("DELETE FROM eci_file_objection_entry"))
        s.execute(text("DELETE FROM eci_file_objection_person"))
        s.execute(text("DELETE FROM eci_file_objection"))

        s.execute(text("DELETE FROM eci_file_selection_person"))
        s.execute(text("DELETE FROM eci_file_selection"))
        s.execute(text("DELETE FROM eci_file_selection_regime"))
        s.execute(text("DELETE FROM eci_file_departure"))
        s.execute(text("DELETE FROM eci_file_person_media"))

        s.execute(text("DELETE FROM eci_file_national_figure"))
        s.execute(text("DELETE FROM eci_file_state_stage"))
        s.execute(text("DELETE FROM eci_file_state"))
        s.execute(text("DELETE FROM eci_file_key_moment"))
        s.execute(text("DELETE FROM eci_file_headline"))
        s.execute(text("DELETE FROM eci_file_citation"))
        s.execute(text("DELETE FROM eci_file_entry_person"))
        s.execute(text("DELETE FROM eci_file_person"))
        s.execute(text("DELETE FROM eci_file_entry"))
        s.execute(text("DELETE FROM eci_file_region"))

        for region in payload.regions:
            s.execute(
                text("""
                    INSERT INTO eci_file_region (slug, name, code, kind, aliases)
                    VALUES (:slug, :name, :code, :kind, CAST(:aliases AS text[]))
                """),
                {
                    "slug": region.slug,
                    "name": region.name,
                    "code": region.code,
                    "kind": region.kind,
                    "aliases": region.aliases,
                },
            )

        for area, entry in payload.entries:
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

        names_by_slug, profile_by_slug, profile_details = _build_people(payload.entries)
        groups = _build_person_groups(names_by_slug, profile_by_slug, profile_details)

        for slug, name in sorted(names_by_slug.items()):
            group = groups[slug]
            s.execute(
                text("""
                    INSERT INTO eci_file_person
                        (slug, name, profile_entry_id, role_group, group_rank, is_current,
                         first_from, last_to)
                    VALUES
                        (:slug, :name, :profile_entry_id, :role_group, :group_rank, :is_current,
                         :first_from, :last_to)
                """),
                {
                    "slug": slug,
                    "name": name,
                    "profile_entry_id": profile_by_slug.get(slug),
                    "role_group": group.role_group,
                    "group_rank": group.group_rank,
                    "is_current": group.is_current,
                    "first_from": group.first_from,
                    "last_to": group.last_to,
                },
            )

        for _, entry in payload.entries:
            for slug in dict.fromkeys(_slugify(name) for name in entry.people):
                s.execute(
                    text("""
                        INSERT INTO eci_file_entry_person (entry_id, person_slug)
                        VALUES (:entry_id, :person_slug)
                    """),
                    {"entry_id": entry.id, "person_slug": slug},
                )

        for _, entry in payload.entries:
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

        for state in payload.states:
            s.execute(
                text("""
                    INSERT INTO eci_file_state (region_slug, phase, exercise, notes)
                    VALUES (:region_slug, :phase, :exercise, :notes)
                """),
                {
                    "region_slug": state.region_slug,
                    "phase": state.phase,
                    "exercise": state.exercise,
                    "notes": state.notes,
                },
            )

        for stage in payload.stages:
            s.execute(
                text("""
                    INSERT INTO eci_file_state_stage
                        (region_slug, stage, electors, as_of, computed, approx, note,
                         source_entry_id, url, tier)
                    VALUES
                        (:region_slug, :stage, :electors, :as_of, :computed, :approx, :note,
                         :source_entry_id, :url, :tier)
                """),
                {
                    "region_slug": stage.region_slug,
                    "stage": stage.stage,
                    "electors": stage.electors,
                    "as_of": stage.as_of,
                    "computed": stage.computed,
                    "approx": stage.approx,
                    "note": stage.note,
                    "source_entry_id": stage.source_entry,
                    "url": stage.url,
                    "tier": stage.tier,
                },
            )

        for figure in payload.national:
            s.execute(
                text("""
                    INSERT INTO eci_file_national_figure
                        (position, grp, measure, label, scope, electors, as_of, computed, approx,
                         source_entry_id, note)
                    VALUES
                        (:position, :grp, :measure, :label, :scope, :electors, :as_of, :computed,
                         :approx, :source_entry_id, :note)
                """),
                {
                    "position": figure.position,
                    "grp": figure.group,
                    "measure": figure.measure,
                    "label": figure.label,
                    "scope": figure.scope,
                    "electors": figure.electors,
                    "as_of": figure.as_of,
                    "computed": figure.computed,
                    "approx": figure.approx,
                    "source_entry_id": figure.source_entry,
                    "note": figure.note,
                },
            )

        if payload.headline is not None:
            for position, stat in enumerate(payload.headline.headline, start=1):
                s.execute(
                    text("""
                        INSERT INTO eci_file_headline
                            (position, value, label, source_label, source_url, entry_id)
                        VALUES
                            (:position, :value, :label, :source_label, :source_url, :entry_id)
                    """),
                    {"position": position, **stat.model_dump()},
                )
            for position, entry_id in enumerate(payload.headline.key_moments, start=1):
                s.execute(
                    text("""
                        INSERT INTO eci_file_key_moment (position, entry_id)
                        VALUES (:position, :entry_id)
                    """),
                    {"position": position, "entry_id": entry_id},
                )

        if payload.selections is not None:
            for position, regime in enumerate(payload.selections.regimes, start=1):
                s.execute(
                    text("""
                        INSERT INTO eci_file_selection_regime
                            (key, position, label, from_date, to_date, rule, panel, entry_ids, notes)
                        VALUES
                            (:key, :position, :label, :from_date, :to_date, :rule,
                             CAST(:panel AS text[]), CAST(:entry_ids AS text[]), :notes)
                    """),
                    {
                        "key": regime.key,
                        "position": position,
                        "label": regime.label,
                        "from_date": regime.from_date,
                        "to_date": regime.to_date,
                        "rule": regime.rule,
                        "panel": regime.panel,
                        "entry_ids": regime.entry_ids,
                        "notes": regime.notes,
                    },
                )

            for position, selection in enumerate(payload.selections.selections, start=1):
                s.execute(
                    text("""
                        INSERT INTO eci_file_selection
                            (id, position, date, date_precision, date_meaning, regime, method,
                             appointed, members, search, dissent, entry_ids, notes)
                        VALUES
                            (:id, :position, :date, :date_precision, :date_meaning, :regime, :method,
                             CAST(:appointed AS jsonb), CAST(:members AS jsonb),
                             CAST(:search AS jsonb), CAST(:dissent AS jsonb),
                             CAST(:entry_ids AS text[]), :notes)
                    """),
                    {
                        "id": selection.id,
                        "position": position,
                        "date": selection.date,
                        "date_precision": selection.date_precision,
                        "date_meaning": selection.date_meaning,
                        "regime": selection.regime,
                        "method": selection.method,
                        "appointed": json.dumps(
                            [a.model_dump(mode="json") for a in selection.appointed]
                        ),
                        "members": json.dumps(
                            [m.model_dump(mode="json") for m in selection.members]
                        ),
                        "search": (
                            json.dumps(selection.search.model_dump(mode="json"))
                            if selection.search is not None
                            else None
                        ),
                        "dissent": json.dumps(
                            [d.model_dump(mode="json") for d in selection.dissent]
                        ),
                        "entry_ids": selection.entry_ids,
                        "notes": selection.notes,
                    },
                )

                for appointee in selection.appointed:
                    s.execute(
                        text("""
                            INSERT INTO eci_file_selection_person (selection_id, person_slug, part)
                            VALUES (:selection_id, :person_slug, 'appointed')
                            ON CONFLICT DO NOTHING
                        """),
                        {"selection_id": selection.id, "person_slug": appointee.person_slug},
                    )
                for member in selection.members:
                    if member.person_slug is not None:
                        s.execute(
                            text("""
                                INSERT INTO eci_file_selection_person
                                    (selection_id, person_slug, part)
                                VALUES (:selection_id, :person_slug, :part)
                                ON CONFLICT DO NOTHING
                            """),
                            {
                                "selection_id": selection.id,
                                "person_slug": member.person_slug,
                                "part": member.part,
                            },
                        )
                if selection.search is not None and selection.search.chair_slug is not None:
                    s.execute(
                        text("""
                            INSERT INTO eci_file_selection_person (selection_id, person_slug, part)
                            VALUES (:selection_id, :person_slug, 'search_chair')
                            ON CONFLICT DO NOTHING
                        """),
                        {
                            "selection_id": selection.id,
                            "person_slug": selection.search.chair_slug,
                        },
                    )

            for departure in payload.selections.departures:
                s.execute(
                    text("""
                        INSERT INTO eci_file_departure
                            (date, person_slug, office, how, notes, entry_ids)
                        VALUES
                            (:date, :person_slug, :office, :how, :notes, CAST(:entry_ids AS text[]))
                    """),
                    {
                        "date": departure.date,
                        "person_slug": departure.person_slug,
                        "office": departure.office,
                        "how": departure.how,
                        "notes": departure.notes,
                        "entry_ids": departure.entry_ids,
                    },
                )

        if payload.media is not None:
            for person in payload.media.people:
                s.execute(
                    text("""
                        INSERT INTO eci_file_person_media
                            (person_slug, url, image_url, source_page, original_source,
                             original_publisher, caption, photo_date, licence, licence_url,
                             licence_review, attribution, self_host)
                        VALUES
                            (:person_slug, :url, :image_url, :source_page, :original_source,
                             :original_publisher, :caption, :photo_date, :licence, :licence_url,
                             :licence_review, :attribution, :self_host)
                    """),
                    {
                        "person_slug": person.slug,
                        "url": person.local_path if person.self_host else person.image_url,
                        "image_url": person.image_url,
                        "source_page": person.source_page,
                        "original_source": person.original_source,
                        "original_publisher": person.original_publisher,
                        "caption": person.caption,
                        "photo_date": person.photo_date,
                        "licence": person.licence,
                        "licence_url": person.licence_url,
                        "licence_review": person.licence_review,
                        "attribution": person.attribution,
                        "self_host": person.self_host,
                    },
                )

        if payload.objections is not None:
            obj = payload.objections
            for o in obj.objections:
                s.execute(
                    text("""
                        INSERT INTO eci_file_objection
                            (n, date, date_precision, concerns, followed_by, public)
                        VALUES (:n, :date, :date_precision, :concerns, :followed_by, :public)
                    """),
                    {
                        "n": o.n,
                        "date": o.date,
                        "date_precision": o.date_precision,
                        "concerns": o.concerns,
                        "followed_by": o.followed_by,
                        "public": o.public,
                    },
                )
                for position, name in enumerate(o.by, start=1):
                    s.execute(
                        text("""
                            INSERT INTO eci_file_objection_person (n, person_slug, position)
                            VALUES (:n, :person_slug, :position)
                        """),
                        {"n": o.n, "person_slug": _slugify(name), "position": position},
                    )
                for position, entry_id in enumerate(o.entry_ids, start=1):
                    s.execute(
                        text("""
                            INSERT INTO eci_file_objection_entry (n, entry_id, position)
                            VALUES (:n, :entry_id, :position)
                        """),
                        {"n": o.n, "entry_id": entry_id, "position": position},
                    )
            s.execute(
                text("""
                    INSERT INTO eci_file_objection_meta
                        (id, missing, notes, report_entry_id, response_entry_id)
                    VALUES (1, :missing, :notes, :report_entry_id, :response_entry_id)
                """),
                {
                    "missing": obj.missing,
                    "notes": obj.notes,
                    "report_entry_id": obj.report_entry_id,
                    "response_entry_id": obj.response_entry_id,
                },
            )

        if payload.pairs is not None:
            for position, pair in enumerate(payload.pairs.pairs, start=1):
                s.execute(
                    text("""
                        INSERT INTO eci_file_pair (charge_id, position, note)
                        VALUES (:charge_id, :position, :note)
                    """),
                    {"charge_id": pair.charge_id, "position": position, "note": pair.note},
                )
                for item_position, entry_id in enumerate(pair.also_recorded_as, start=1):
                    s.execute(
                        text("""
                            INSERT INTO eci_file_pair_item
                                (charge_id, entry_id, role, position, why)
                            VALUES (:charge_id, :entry_id, 'same', :position, NULL)
                        """),
                        {
                            "charge_id": pair.charge_id,
                            "entry_id": entry_id,
                            "position": item_position,
                        },
                    )
                for item_position, entry_id in enumerate(pair.response_ids, start=1):
                    s.execute(
                        text("""
                            INSERT INTO eci_file_pair_item
                                (charge_id, entry_id, role, position, why)
                            VALUES (:charge_id, :entry_id, 'response', :position, NULL)
                        """),
                        {
                            "charge_id": pair.charge_id,
                            "entry_id": entry_id,
                            "position": item_position,
                        },
                    )
                for item_position, entry_id in enumerate(pair.record_ids, start=1):
                    s.execute(
                        text("""
                            INSERT INTO eci_file_pair_item
                                (charge_id, entry_id, role, position, why)
                            VALUES (:charge_id, :entry_id, 'record', :position, NULL)
                        """),
                        {
                            "charge_id": pair.charge_id,
                            "entry_id": entry_id,
                            "position": item_position,
                        },
                    )
                for item_position, rel in enumerate(pair.related, start=1):
                    s.execute(
                        text("""
                            INSERT INTO eci_file_pair_item
                                (charge_id, entry_id, role, position, why)
                            VALUES (:charge_id, :entry_id, 'related', :position, :why)
                        """),
                        {
                            "charge_id": pair.charge_id,
                            "entry_id": rel.id,
                            "position": item_position,
                            "why": rel.why,
                        },
                    )

            for unpaired in payload.pairs.unpaired_responses:
                s.execute(
                    text("""
                        INSERT INTO eci_file_unpaired_response (response_entry_id, note)
                        VALUES (:response_entry_id, :note)
                    """),
                    {"response_entry_id": unpaired.response_id, "note": unpaired.note},
                )

        if payload.rule_diffs is not None:
            for position, d in enumerate(payload.rule_diffs.diffs, start=1):
                s.execute(
                    text("""
                        INSERT INTO eci_file_rule_diff
                            (id, position, rule_entry_id, title, document, before_label,
                             after_label, before_lines, after_lines, before_status, after_status,
                             text_status, excerpt, quoted_lines_before, quoted_lines_after,
                             source_urls, note)
                        VALUES
                            (:id, :position, :rule_entry_id, :title, :document, :before_label,
                             :after_label, CAST(:before_lines AS text[]), CAST(:after_lines AS text[]),
                             :before_status, :after_status, :text_status, :excerpt,
                             CAST(:quoted_lines_before AS smallint[]),
                             CAST(:quoted_lines_after AS smallint[]),
                             CAST(:source_urls AS text[]), :note)
                    """),
                    {
                        "id": d.id,
                        "position": position,
                        "rule_entry_id": d.rule_entry_id,
                        "title": d.title,
                        "document": d.document,
                        "before_label": d.before_label,
                        "after_label": d.after_label,
                        "before_lines": d.before,
                        "after_lines": d.after,
                        "before_status": d.before_status,
                        "after_status": d.after_status,
                        "text_status": d.text_status,
                        "excerpt": d.excerpt,
                        "quoted_lines_before": d.quoted_lines_before,
                        "quoted_lines_after": d.quoted_lines_after,
                        "source_urls": d.source_urls,
                        "note": d.note,
                    },
                )
                for entry_id in d.related_entry_ids:
                    s.execute(
                        text("""
                            INSERT INTO eci_file_rule_diff_entry (diff_id, entry_id)
                            VALUES (:diff_id, :entry_id)
                        """),
                        {"diff_id": d.id, "entry_id": entry_id},
                    )

        if payload.cases is not None:
            for position, case in enumerate(payload.cases.cases, start=1):
                s.execute(
                    text("""
                        INSERT INTO eci_file_case
                            (slug, position, short_name, case_entry_id, court, short_status,
                             status_note, parties)
                        VALUES
                            (:slug, :position, :short_name, :case_entry_id, :court, :short_status,
                             :status_note, CAST(:parties AS jsonb))
                    """),
                    {
                        "slug": case.slug,
                        "position": position,
                        "short_name": case.short_name,
                        "case_entry_id": case.case_entry_id,
                        "court": case.court,
                        "short_status": case.short_status,
                        "status_note": case.status_note,
                        "parties": json.dumps(case.parties.model_dump(mode="json")),
                    },
                )
                for item in case.items:
                    s.execute(
                        text("""
                            INSERT INTO eci_file_case_item (case_slug, entry_id, role, note)
                            VALUES (:case_slug, :entry_id, :role, :note)
                        """),
                        {
                            "case_slug": case.slug,
                            "entry_id": item.entry_id,
                            "role": item.role,
                            "note": item.note,
                        },
                    )


def run(
    path: str | Path | None = None,
    states_path: str | Path | None = None,
    headline_path: str | Path | None = None,
    regions_path: str | Path | None = None,
    national_path: str | Path | None = None,
    selections_path: str | Path | None = None,
    media_path: str | Path | None = None,
    objections_path: str | Path | None = None,
    pairs_path: str | Path | None = None,
    rule_diffs_path: str | Path | None = None,
    cases_path: str | Path | None = None,
    merges_path: str | Path | None = None,
) -> None:
    payload, errors = validate_all(
        path=path,
        states_path=states_path,
        headline_path=headline_path,
        regions_path=regions_path,
        national_path=national_path,
        selections_path=selections_path,
        media_path=media_path,
        objections_path=objections_path,
        pairs_path=pairs_path,
        rule_diffs_path=rule_diffs_path,
        cases_path=cases_path,
        merges_path=merges_path,
    )
    if errors:
        raise EciFilesValidationError(errors)
    assert payload is not None

    _replace_all(payload)

    entries = [entry for _, entry in payload.entries]
    people = {name for e in entries for name in e.people} | {
        _profile_name(e) for e in entries if e.kind == "person"
    }
    citations = sum(len(e.sources) for e in entries)
    checked = sum(1 for e in entries if e.check == "checked")
    print(
        f"[eci-files] loaded {len(entries)} entries, {len(people)} people, {citations} citations "
        f"({checked} checked, {len(entries) - checked} unchecked)"
    )
    print(
        f"[eci-files] loaded {len(payload.regions)} regions, "
        f"{len({s.region_slug for s in payload.stages})} states with figures, "
        f"{len(payload.national)} national figures"
    )
    if payload.headline is not None:
        print(f"[eci-files] loaded {len(payload.headline.headline)} headline stats, "
              f"{len(payload.headline.key_moments)} key moments")
    if payload.selections is not None:
        print(
            f"[eci-files] loaded {len(payload.selections.regimes)} regimes, "
            f"{len(payload.selections.selections)} selections, "
            f"{len(payload.selections.departures)} departures, "
            f"{len(payload.media.people) if payload.media is not None else 0} photos"
        )
    print(f"[eci-files] resolved {payload.resolved_response_count} response links through merges.json")
    if (
        payload.objections is not None
        and payload.pairs is not None
        and payload.rule_diffs is not None
        and payload.cases is not None
    ):
        without_response = sum(1 for p in payload.pairs.pairs if not p.response_ids)
        total_case_items = sum(len(c.items) for c in payload.cases.cases)
        print(
            f"[eci-files] loaded {len(payload.objections.objections)} objections "
            f"({payload.objections.missing} missing), "
            f"{len(payload.pairs.pairs)} pairs ({without_response} without a response), "
            f"{len(payload.rule_diffs.diffs)} rule diffs, "
            f"{len(payload.cases.cases)} cases ({total_case_items} items)"
        )
