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

// --- ECI Files phase 5 (views) ---
// Hand-written against docs/eci-files/PHASE5-SPEC.md §4 (schemas.py isn't written yet — the backend
// worker owns that file; these are narrowed by hand and should be replaced by the generated equivalents
// once `npm run codegen` picks them up). `EciEntryRef`, `EciPhoto` and `EciPersonWithPhoto` are phase 4's
// shapes: phase 4 hadn't landed on this branch when phase 5 started, so they're hand-written here too,
// under the same names phase 4's spec uses, so a rebase can drop this copy in favour of phase 4's.

/** A photo credited to one of the five reviewer-confirmed Commons portraits (PHASES-3-5-DECISIONS.md).
 *  Phase 4's shape — redefined here only because phase 4 hasn't landed on this branch yet. */
export interface EciPhoto {
  url: string;
  attribution: string | null;
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
