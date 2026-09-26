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

export interface EciPersonSummary {
  slug: string;
  name: string;
  role: string | null;
  tenure: EciTenure[];
  entry_count: number;
}

export interface EciPersonPage {
  person: { slug: string; name: string; profile: EciEntry | null };
  entries: EciEntry[];
}

// --- ECI Files phase 3 (numbers) ---
// Hand-written against docs/eci-files/PHASE3-SPEC.md §2.4 — the backend worker is building
// `/eci-files/states` and the `timeline?state=` facet in parallel, so these aren't in src/types/api.ts
// yet. Re-run `npm run codegen` and drop the hand-written versions once it lands.

export type EciStage = "before" | "draft" | "final" | "appeals_filed" | "appeals_pending" | "restored";
export type EciRegionKind = "state" | "ut";
export type EciExercise = "sir" | "special_revision";
export type EciNationalGroup = "all" | "phase_1" | "phase_2" | "phase_3";
export type EciNationalMeasure = "before" | "draft" | "final" | "left_off" | "net_fall";

export interface EciStageValue {
  stage: EciStage;
  electors: number;
  as_of: string | null;
  computed: boolean;
  approx: boolean;
  note: string | null;
  source_entry_id: string;
  source_entry_title: string;
  source_status: EciEntryStatus;
  url: string;
  tier: number;
}

export interface EciStateMetric {
  /** Percent, rounded to 2dp; signed for `net_change`. */
  value: number;
  /** Electors; signed for `net_change`. */
  count: number;
  /** The denominator, in electors. */
  base: number;
  /** OR of the contributing stages' `computed`. */
  computed: boolean;
  /** OR of the contributing stages' `approx`. */
  approx: boolean;
  /** True if any contributing stage carries a note. */
  noted: boolean;
}

export interface EciStateMetrics {
  draft_left_off?: EciStateMetric | null;
  net_change?: EciStateMetric | null;
  /** Kept in the schema and shown on state pages; PHASES-3-5-DECISIONS.md drops it as a
   *  /eci-files/numbers tile measure, so nothing in eci-numbers.ts's ECI_METRICS reads this key. */
  appeals_filed?: EciStateMetric | null;
}

export interface EciRegionSummary {
  slug: string;
  name: string;
  code: string;
  kind: EciRegionKind;
  phase: number | null;
  exercise: EciExercise | null;
  has_figures: boolean;
  entry_count: number;
  /** Canonical order: before, draft, final, appeals_filed, appeals_pending, restored. */
  stages: EciStageValue[];
  metrics: EciStateMetrics;
}

export interface EciNationalFigure {
  group: EciNationalGroup;
  measure: EciNationalMeasure;
  label: string;
  scope: string;
  electors: number;
  as_of: string | null;
  computed: boolean;
  approx: boolean;
  note: string | null;
  source_entry_id: string;
  source_entry_title: string;
  source_status: EciEntryStatus;
}

export interface EciStatesOverview {
  regions: EciRegionSummary[];
  national: EciNationalFigure[];
  last_as_of: string | null;
}

export interface EciStatePage {
  region: EciRegionSummary;
  notes: string | null;
}

export interface EciStateCount {
  slug: string;
  name: string;
  count: number;
}

// Declaration merging (not an edit to the `EciTimelineOf<E>` declared above) — adds the phase 3 `states`
// facet (PHASE3-SPEC.md §2.3) to both EciTimeline and EciCompactTimeline without touching the phase 2
// text, since phase 4 and 5 web workers edit this same file in parallel.
// eslint-disable-next-line @typescript-eslint/no-unused-vars -- <E> must match the merged declaration above
export interface EciTimelineOf<E> {
  states: EciStateCount[];
}
// --- end phase 3 ---
