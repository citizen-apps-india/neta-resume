/**
 * Narrowed types for the ECI Files API (`api/neta_api/schemas.py`, generated as `components["schemas"]["Eci*"]`
 * in `src/types/api.ts`). The generated types leave every defaulted field optional and every enum a plain
 * string; these narrow them. Keep them in step with the generated file when the API changes.
 *
 * `EciFilesLane`, `EciCompactEntry`, `EciLaneCount`, `EciHeadlineStat`, `EciSummary` and `EciDensity` (plus
 * `lane` on `EciEntry`) are hand-written against `docs/eci-files/REDESIGN-SPEC.md` — the "Phase 2" API
 * (`/eci-files/summary`, `/eci-files/density`, `timeline?lane=&fields=compact`) is being built in parallel
 * by the backend worker and isn't in `src/types/api.ts` yet. Re-run `npm run codegen` and drop the
 * hand-written versions once it lands.
 */

export type EciEntryKind = "event" | "person" | "rule" | "figure" | "case" | "statement";
export type EciEntryStatus = "documented" | "reported" | "claim" | "response";
export type EciDatePrecision = "day" | "month" | "year";
export type EciCheckStatus = "checked" | "unchecked";

/** The five reading lanes (`docs/eci-files/REDESIGN-SPEC.md` §1a) — derived by the loader, one per entry.
 *  Precedence: responses > claims > courts > inside > commission (the last is the catch-all). */
export type EciFilesLane = "responses" | "claims" | "courts" | "inside" | "commission";

export interface EciFigure {
  label: string;
  value: number;
  unit: string;
  as_of: string | null;
}

export interface EciEntryPerson {
  slug: string;
  name: string;
}

/** A stub reference to a response entry, embedded on the charge it answers. */
export interface EciResponseRef {
  id: string;
  title: string;
  date: string | null;
}

export interface EciCitation {
  position: number;
  url: string;
  publisher: string | null;
  title: string | null;
  published: string | null;
  tier: 1 | 2 | 3;
  archive_url: string | null;
  quote: string | null;
}

export interface EciEntry {
  id: string;
  area: string;
  kind: EciEntryKind;
  date: string | null;
  date_precision: EciDatePrecision;
  title: string;
  summary: string;
  status: EciEntryStatus;
  lane: EciFilesLane;
  attributed_to: string | null;
  topics: string[];
  states: string[];
  figures: EciFigure[];
  details: Record<string, unknown>;
  notes: string | null;
  check_status: EciCheckStatus;
  people: EciEntryPerson[];
  response_to: string | null;
  responses: EciResponseRef[];
  citations: EciCitation[];
}

/** The `fields=compact` shape of `GET /eci-files/timeline` (REDESIGN-SPEC §"API (backend worker)") — just
 *  enough to place and label a dot. No citations, no summary: the drawer fetches the full {@link EciEntry}
 *  separately, so the first paint of the lane timeline never pulls the whole record over the wire. */
export interface EciCompactEntry {
  id: string;
  date: string | null;
  date_precision: EciDatePrecision;
  title: string;
  status: EciEntryStatus;
  lane: EciFilesLane;
  check_status: EciCheckStatus;
  people: EciEntryPerson[];
}

export interface EciTopicCount {
  topic: string;
  count: number;
}

export interface EciPersonCount {
  slug: string;
  name: string;
  count: number;
}

export interface EciLaneCount {
  lane: EciFilesLane;
  count: number;
}

export interface EciTimelineCounts {
  checked: number;
  unchecked: number;
}

/** `GET /eci-files/timeline` — generic over the entry shape so one type covers both the full-detail
 *  fetch (`/eci-files/entries`, `EciEntry`) and the dot-drawing fetch (`fields=compact`, {@link EciCompactEntry}). */
export interface EciTimelineOf<E> {
  entries: E[];
  topics: EciTopicCount[];
  people: EciPersonCount[];
  lanes: EciLaneCount[];
  counts: EciTimelineCounts;
}

export type EciTimeline = EciTimelineOf<EciEntry>;
export type EciCompactTimeline = EciTimelineOf<EciCompactEntry>;

/** One headline stat on the `/eci-files` front page — a curated figure from `data/eci_files/headline.json`,
 *  always carrying its own source (REDESIGN-SPEC §"API (backend worker)": "Every number needs a source"). */
export interface EciHeadlineStat {
  value: string;
  label: string;
  source_label: string;
  source_url: string;
  entry_id: string;
}

export interface EciSummaryCounts {
  entries: number;
  checked: number;
  people: number;
  citations: number;
}

/** `GET /eci-files/summary` — the front page's payload: the four headline stats, ~8 key-moment entries,
 *  record-wide counts, and when the record was last loaded. */
export interface EciSummary {
  headline: EciHeadlineStat[];
  key_moments: EciEntry[];
  counts: EciSummaryCounts;
  last_loaded: string | null;
}

export interface EciDensityBucket {
  month: string;
  lane: EciFilesLane;
  count: number;
}

/** `GET /eci-files/density` — one row per (month, lane), for the timeline's overview strip. */
export interface EciDensity {
  months: EciDensityBucket[];
}

export interface EciTenure {
  office?: string | null;
  from?: string | null;
  to?: string | null;
}

export interface EciCareerLine {
  from?: string | null;
  to?: string | null;
  post?: string | null;
  source_url?: string | null;
}

// `EciPersonSummary` and `EciPersonPage` below are the phase 4 (`PHASE4-SPEC.md` §5.4) shapes of
// `GET /eci-files/people` and `GET /eci-files/people/{slug}` — grouped, ranked and photo-bearing, replacing
// the phase-2 stubs. Exclusively phase 4's concern (no other phase reads or writes these two types), so
// they're updated in place rather than appended. See the phase 4 block at the end of this file for the
// types they reference (`EciPersonGroup`, `EciStatusCounts`, `EciPhoto`, `EciSelection`, `EciEntryRef`).

export interface EciPersonSummary {
  slug: string;
  name: string;
  group: EciPersonGroup;
  group_rank: number;
  current: boolean;
  role: string | null;
  service: string | null;
  tenure: EciTenure[];
  first_from: string | null;
  last_to: string | null;
  entry_count: number;
  status_counts: EciStatusCounts;
  photo: EciPhoto | null;
}

export interface EciPersonDetail {
  slug: string;
  name: string;
  profile: EciEntry | null;
  group: EciPersonGroup;
  current: boolean;
  role: string | null;
  service: string | null;
  tenure: EciTenure[];
  status_counts: EciStatusCounts;
  photo: EciPhoto | null;
}

export interface EciPersonPage {
  person: EciPersonDetail;
  entries: EciEntry[];
  selections: EciSelection[];
  entries_index: EciEntryRef[];
}

// --- ECI Files phase 4 (people) ---
// `/eci-files/people`, `/eci-files/people/[slug]` and `/eci-files/selections` (`PHASE4-SPEC.md` §5.4).
// Hand-written against the spec's Pydantic models ahead of the backend landing; narrow, never widen, once
// `npm run codegen` produces the generated equivalents in `src/types/api.ts`.

/** Where a person sits on `/eci-files/people` (`PHASE4-SPEC.md` §1.4) — derived by the loader. */
export type EciPersonGroup = "commission" | "secretariat" | "state" | "named";

export interface EciPhoto {
  url: string;
  source_page: string;
  attribution: string;
  licence: string;
  licence_url: string;
  licence_review: "reviewed" | "uploader_asserted";
  original_publisher: string | null;
  caption: string | null;
  photo_date: string | null;
}

export interface EciStatusCounts {
  documented: number;
  reported: number;
  claim: number;
  response: number;
}

/** A labelled reference to an entry cited elsewhere (a selection, a departure) without pulling in the
 *  whole {@link EciEntry} — enough to render "Cited: {title}" and open the drawer by id. */
export interface EciEntryRef {
  id: string;
  title: string;
  date: string | null;
  date_precision: EciDatePrecision;
  status: EciEntryStatus;
}

export type EciSelectionPart = "recommended" | "proposed" | "voted_with_majority" | "dissented" | "search_chair";
export type EciSelectionMethod = "executive_appointment" | "elevation_of_senior_ec" | "selection_committee";
export type EciSelectionRegimeKey = "convention" | "baranwal" | "act_2023";

export interface EciSelectionAppointee {
  person_slug: string;
  name: string;
  office: string;
  took_charge: string | null;
  replaced: string | null;
  photo: EciPhoto | null;
}

export interface EciSelectionMember {
  person_slug: string | null;
  name: string | null;
  role: string;
  part: EciSelectionPart;
  has_profile: boolean;
  entry_ids: string[];
}

export interface EciSelectionSearch {
  by: string;
  chair_slug: string | null;
  shortlist_size: number | null;
  shortlist: string[] | null;
  shortlist_source: string | null;
  entry_ids: string[];
}

export interface EciSelectionDissent {
  person_slug: string;
  name: string;
  summary: string;
  note_public: boolean;
  status: EciEntryStatus;
  entry_ids: string[];
  response_entry_ids: string[];
}

export interface EciSelection {
  id: string;
  date: string;
  date_precision: EciDatePrecision;
  date_meaning: string | null;
  regime: EciSelectionRegimeKey;
  method: EciSelectionMethod;
  appointed: EciSelectionAppointee[];
  members: EciSelectionMember[];
  search: EciSelectionSearch | null;
  dissent: EciSelectionDissent[];
  entry_ids: string[];
  notes: string | null;
}

export interface EciSelectionRegime {
  key: EciSelectionRegimeKey;
  label: string;
  from_date: string | null;
  to_date: string | null;
  rule: string;
  panel: string[];
  entry_ids: string[];
  notes: string | null;
  selection_count: number;
}

export interface EciDeparture {
  date: string;
  person_slug: string;
  name: string;
  office: string;
  how: "resigned" | "tenure_ended";
  notes: string | null;
  entry_ids: string[];
}

/** `GET /eci-files/selections`. `gaps` isn't in PHASE4-SPEC.md §5.4's Pydantic listing, but §3 step 6
 *  requires rendering "What the record doesn't show" from "the file's `gaps[]`" — `selections.json` carries
 *  it at the top level, so it's added here as the one field the spec's page requirement needs that its own
 *  schema section omitted. Flagged for the backend worker to add to `EciSelections` in `schemas.py`. */
export interface EciSelections {
  regimes: EciSelectionRegime[];
  selections: EciSelection[];
  departures: EciDeparture[];
  entries_index: EciEntryRef[];
  gaps: string[];
}
// --- end phase 4 ---
