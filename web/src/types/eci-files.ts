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

/** A stub reference to any entry — enough to render a dated, titled link with its status, without
 *  pulling the full {@link EciEntry}. Phase 4's shape, plus phase 5's `check_status` addition. */
export interface EciEntryRef {
  id: string;
  title: string;
  date: string | null;
  date_precision: EciDatePrecision;
  status: EciEntryStatus;
  check_status: EciCheckStatus | null;
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

// --- ECI Files phase 5 (views) ---
// Hand-written against docs/eci-files/PHASE5-SPEC.md §4 (schemas.py isn't written yet — the backend
// worker owns that file; these are narrowed by hand and should be replaced by the generated equivalents
// once `npm run codegen` picks them up). `EciEntryRef`, `EciPhoto` and `EciPersonWithPhoto` are phase 4's
// shapes: phase 4 hadn't landed on this branch when phase 5 started, so they're hand-written here too,
// under the same names phase 4's spec uses, so a rebase can drop this copy in favour of phase 4's.



/** Enough of an entry for a row or a cell — the drawer fetches the full {@link EciEntry} separately. */
export interface EciEntryCard {
  id: string;
  kind: EciEntryKind;
  date: string | null;
  date_precision: EciDatePrecision;
  title: string;
  summary: string;
  status: EciEntryStatus;
  lane: EciFilesLane;
  attributed_to: string | null;
  check_status: EciCheckStatus;
  people: EciEntryPerson[];
  citation_count: number;
  lead_citation: EciCitation | null;
}

/** Phase 4's shape — a person with their photo (or none, when the licence isn't confirmed yet). */
export interface EciPersonWithPhoto {
  slug: string;
  name: string;
  photo: EciPhoto | null;
}

// ---- /eci-files/objections ----

export interface EciObjection {
  n: number;
  date: string | null;
  date_precision: EciDatePrecision;
  by: EciPersonWithPhoto[];
  concerns: string;
  followed_by: string | null;
  followed_by_refs: EciEntryRef[];
  public: boolean;
  entries: EciEntryRef[];
}

export interface EciObjectionPersonCount {
  slug: string;
  name: string;
  photo: EciPhoto | null;
  count: number;
  joint: number;
}

export interface EciObjectionsPage {
  identified: number;
  missing: number;
  reported_total: number;
  notes: string | null;
  report: EciEntryRef | null;
  response: EciEntryCard | null;
  objections: EciObjection[];
  by_person: EciObjectionPersonCount[];
}

// ---- /eci-files/answers ----

export interface EciRelatedRef {
  entry: EciEntryRef;
  why: string;
}

export interface EciAnswerRow {
  charge: EciEntryCard;
  also_recorded_as: EciEntryRef[];
  responses: EciEntryCard[];
  record: EciEntryCard[];
  related: EciRelatedRef[];
  note: string | null;
  curated: boolean;
}

export interface EciAnswersCounts {
  rows: number;
  with_response: number;
  without_response: number;
  with_record: number;
}

export interface EciUnpairedResponse {
  response: EciEntryCard;
  note: string | null;
}

export interface EciAnswersPage {
  counts: EciAnswersCounts;
  rows: EciAnswerRow[];
  unpaired_responses: EciUnpairedResponse[];
}

export type EciAnswersView = "all" | "no-response" | "with-record";

// ---- /eci-files/rules ----

export type EciTextStatus = "verbatim" | "quoted in reporting" | "paraphrased from reporting";

export interface EciRuleDiffRef {
  id: string;
  title: string;
  text_status: EciTextStatus;
}

export interface EciRuleRow {
  entry: EciEntryCard;
  diffs: EciRuleDiffRef[];
}

export interface EciRulesPage {
  rules: EciRuleRow[];
  diffs: EciRuleDiffRef[];
  counts: { rules: number; with_diff: number; diffs: number };
}

export interface EciRuleDiff {
  id: string;
  title: string;
  document: string;
  rule_entry: EciEntryCard;
  before_label: string;
  after_label: string;
  before: string[];
  after: string[];
  before_status: EciTextStatus;
  after_status: EciTextStatus;
  text_status: EciTextStatus;
  excerpt: boolean;
  quoted_lines_before: number[];
  quoted_lines_after: number[];
  source_urls: string[];
  note: string | null;
  related: EciEntryRef[];
}

// ---- /eci-files/courts ----

export type EciCaseShortStatus = "pending" | "disposed" | "referred";
export type EciCaseRole = "order" | "judgment" | "hearing" | "filing" | "listing" | "recusal" | "compliance" | "related";

export interface EciCaseSummary {
  slug: string;
  short_name: string;
  title: string;
  case_number: string | null;
  court: string;
  short_status: EciCaseShortStatus;
  status_note: string | null;
  item_count: number;
  order_count: number;
  first_date: string | null;
  last_date: string | null;
  latest: EciEntryRef | null;
}

export interface EciCourtsPage {
  cases: EciCaseSummary[];
  other_court_entries: number;
}

export interface EciCaseItem {
  role: EciCaseRole;
  note: string | null;
  entry: EciEntryCard;
}

export interface EciCaseParties {
  petitioners: string[];
  respondents: string[];
}

export interface EciCasePage {
  slug: string;
  short_name: string;
  court: string;
  short_status: EciCaseShortStatus;
  status_note: string | null;
  case: EciEntry;
  case_name: string;
  case_number: string | null;
  bench: string | null;
  citation: string | null;
  parties: EciCaseParties;
  items: EciCaseItem[];
}

// ---- /eci-files/entries/{id} context (drawer) ----

export interface EciPairContext {
  charge: EciEntryRef;
  role: "charge" | "response" | "record" | "related" | "same";
  responses: EciEntryRef[];
  record: EciEntryRef[];
  note: string | null;
}

export interface EciEntryCaseContext {
  slug: string;
  short_name: string;
  role: EciCaseRole;
}

export interface EciEntryObjectionContext {
  n: number;
  concerns: string;
}

export interface EciEntryContext {
  pairs: EciPairContext[];
  case: EciEntryCaseContext | null;
  objections: EciEntryObjectionContext[];
  rule_diffs: EciRuleDiffRef[];
}

/** `GET /eci-files/entries/{id}` — the same `EciEntry` plus the cross-references phase 5's views need
 *  (`context`). Every other route still returns plain {@link EciEntry}, so timeline payloads don't grow. */
export interface EciEntryDetail extends EciEntry {
  context: EciEntryContext;
}
// --- end phase 5 ---

// --- launch fixdata ---
// S11: a pair's classification. "charge" (the default a synthesised row always carries) is a charge
// against the Commission or a named person; "defence" is a statement defending the Commission (e.g. a
// party spokesperson) and "analysis" is a third party's analysis (e.g. PRS on a bill) — neither is a
// charge. The API's `counts` (rows/with_response/without_response/with_record) and the `?view=
// no-response` filter are computed over `kind === "charge"` rows only; `kind !== "charge"` rows still
// come back in `rows` for `view=all` so the page can render them, but the web fixer must keep them out
// of the "charges" / "no response" groupings and instead render them in their own small group (e.g.
// "Also on the record: defence and analysis") or as inline context, so the no-response count reads as
// it's counted, not inflated by rows that were never charges.
export interface EciAnswerRow {
  kind: "charge" | "defence" | "analysis";
}
/** Entries that sit on the timeline: the record minus the person profiles. */
export interface EciSummaryCounts {
  dated_entries?: number;
}
// --- end launch fixdata ---
