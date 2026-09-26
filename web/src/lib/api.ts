// Typed client for the FastAPI read layer. Called from server components (no DB creds in browser).
// The types below are ALIASES over the OpenAPI-generated contract in src/types/api.ts — the single
// source of truth is api/neta_api/schemas.py. After changing the API schema, run `npm run codegen`
// (with the API running) to refresh src/types/api.ts; these aliases then pick the changes up.

import type { components } from "@/types/api";
import type {
  EciTimeline,
  EciCompactTimeline,
  EciSummary,
  EciDensity,
  EciPersonSummary,
  EciPersonPage,
  EciEntry,
} from "@/types/eci-files";

const API_BASE = process.env.NETA_API_BASE ?? "http://localhost:8000";

type Schemas = components["schemas"];
export type Source = Schemas["Source"];
export type OfficeTerm = Schemas["OfficeTerm"];
export type PartyStint = Schemas["PartyStint"];
export type AffidavitWealth = Schemas["AffidavitWealth"];
export type CriminalCase = Schemas["CriminalCase"];
export type PartySwitch = Schemas["PartySwitch"];
export type PersonResume = Schemas["PersonResume"];
export type PersonSummary = Schemas["PersonSummary"];
export type ParliamentaryActivity = Schemas["ParliamentaryActivity"];
export type ParliamentaryRecord = Schemas["ParliamentaryRecord"];
export type ParliamentaryQuestion = Schemas["ParliamentaryQuestion"];
export type ThemeFocus = Schemas["ThemeFocus"];

async function getJSON<T>(path: string, revalidate = 3600): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { next: { revalidate } });
  if (!res.ok) throw new Error(`API ${res.status} for ${path}`);
  return res.json();
}

export async function getPersonResume(id: number): Promise<PersonResume | null> {
  const res = await fetch(`${API_BASE}/persons/${id}`, { next: { revalidate: 3600 } });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

export type ListPersonsOpts = {
  limit?: number; offset?: number; house?: string; state?: string; constituency?: string;
  jurisdiction?: string; party?: string; cases?: string; q?: string; theme?: string; cycle?: number; sort?: string; revalidate?: number;
};

/** A page of legislators plus the total count of matches (from the X-Total-Count header) for paging. */
export async function listPersons(opts: ListPersonsOpts = {}): Promise<{ items: PersonSummary[]; total: number }> {
  const q = new URLSearchParams();
  q.set("limit", String(opts.limit ?? 60));
  q.set("offset", String(opts.offset ?? 0));
  if (opts.house) q.set("house", opts.house);
  if (opts.state) q.set("state", opts.state);
  if (opts.constituency) q.set("constituency", opts.constituency);
  if (opts.jurisdiction) q.set("jurisdiction", opts.jurisdiction);
  if (opts.party) q.set("party", opts.party);
  if (opts.cases) q.set("cases", opts.cases);
  if (opts.q) q.set("q", opts.q);
  if (opts.theme) q.set("theme", opts.theme);
  if (opts.cycle) q.set("cycle", String(opts.cycle));
  if (opts.sort) q.set("sort", opts.sort);
  const res = await fetch(`${API_BASE}/persons?${q.toString()}`, { next: { revalidate: opts.revalidate ?? 3600 } });
  if (!res.ok) throw new Error(`API ${res.status} for /persons`);
  const items = (await res.json()) as PersonSummary[];
  const total = Number(res.headers.get("x-total-count") ?? items.length);
  return { items, total };
}

/** Dropdown option lists (party / state / house / LS session, each with a count) for a browse scope. */
export type FacetCount = { value: string; count: number };
export type Facets = { parties: FacetCount[]; states: FacetCount[]; houses: FacetCount[]; themes: FacetCount[]; cycles: FacetCount[] };
export function getFacets(
  opts: { house?: string; state?: string; jurisdiction?: string; cycle?: number } = {},
): Promise<Facets> {
  const q = new URLSearchParams();
  if (opts.house) q.set("house", opts.house);
  if (opts.state) q.set("state", opts.state);
  if (opts.jurisdiction) q.set("jurisdiction", opts.jurisdiction);
  if (opts.cycle) q.set("cycle", String(opts.cycle));
  return getJSON<Facets>(`/persons/facets?${q.toString()}`, 3600);
}

export function searchPersons(q: string): Promise<PersonSummary[]> {
  // Short ISR (5 min): repeated queries collapse onto one cached API response; new ingests still surface
  // within minutes. Was always-live (0), which meant every keystroke-driven search hit Render cold.
  return getJSON<PersonSummary[]>(`/search?q=${encodeURIComponent(q)}`, 300);
}

/** Headline counts for the homepage (real totals, not capped by a list limit). */
export type Stats = {
  total_legislators: number;
  lok_sabha: number;
  rajya_sabha: number;
  with_cases: number;
  crorepatis: number;
};
export function getStats(): Promise<Stats> {
  return getJSON<Stats>("/stats", 600);
}

// "Parliament functioning" section aggregates.
export type ThemeCount = { theme: string; count: number };
export type MinistryCount = { ministry: string; theme: string; count: number };
export type MpCount = { id: number; display_name: string; photo_url: string | null; count: number; top_theme: string | null };
export type ParliamentStats = {
  house: string; total_questions: number; total_debates: number; active_mps: number;
  themes: ThemeCount[]; top_ministries: MinistryCount[]; most_active: MpCount[];
};
export type House = "ls" | "rs";
export function getParliamentStats(house: House = "ls"): Promise<ParliamentStats> {
  return getJSON<ParliamentStats>(`/parliament/stats?house=${house}`, 3600);
}
export function getParliamentMinistries(house: House = "ls"): Promise<MinistryCount[]> {
  return getJSON<MinistryCount[]>(`/parliament/ministries?house=${house}`, 3600);
}

// Topic search over question subjects + debate titles (18th Lok Sabha).
export type RecordHit = {
  kind: "question" | "debate";
  id: number;
  title: string | null;
  mp_id: number;
  mp_name: string;
  ministry: string | null;
  theme: string | null;
  date: string | null;
};
export type SearchRecordsOpts = { q: string; kind?: string; theme?: string; limit?: number; offset?: number; house?: House };
/** A page of matching questions/debates plus the total match count (from X-Total-Count). */
export async function searchRecords(opts: SearchRecordsOpts): Promise<{ items: RecordHit[]; total: number }> {
  const p = new URLSearchParams();
  p.set("q", opts.q);
  if (opts.kind) p.set("kind", opts.kind);
  if (opts.theme) p.set("theme", opts.theme);
  if (opts.house) p.set("house", opts.house);
  p.set("limit", String(opts.limit ?? 30));
  p.set("offset", String(opts.offset ?? 0));
  const res = await fetch(`${API_BASE}/parliament/search?${p.toString()}`, { next: { revalidate: 3600 } });
  if (!res.ok) throw new Error(`API ${res.status} for /parliament/search`);
  const items = (await res.json()) as RecordHit[];
  const total = Number(res.headers.get("x-total-count") ?? items.length);
  return { items, total };
}

// Monthly question volume split by policy theme (stacked-area trends).
export type ThemeSeries = { theme: string; points: number[] };
export type Trends = { house: string; months: string[]; totals: number[]; series: ThemeSeries[] };
export function getParliamentTrends(house: House = "ls"): Promise<Trends> {
  return getJSON<Trends>(`/parliament/trends?house=${house}`, 3600);
}

// Collective theme-emphasis breakdown by party / state (descriptive, share-based).
export type ThemeShare = { theme: string; count: number; share: number };
export type AggregateGroup = { key: string; total: number; mps: number; themes: ThemeShare[] };
export type ThemeFocusBreakdown = { by: "party" | "state"; house: string; groups: AggregateGroup[] };
export function getThemeFocus(by: "party" | "state", house: House = "ls"): Promise<ThemeFocusBreakdown> {
  return getJSON<ThemeFocusBreakdown>(`/aggregate/theme-focus?by=${by}&house=${house}`, 3600);
}

// India Dashboard: country-level macro indicators (World Bank v1), grouped by curated category.
export type IndicatorPoint = Schemas["IndicatorPoint"];
export type IndicatorSeries = Schemas["IndicatorSeries"];
export type IndicatorCategory = Schemas["IndicatorCategory"];
export type IndiaDashboard = Schemas["IndiaDashboard"];
export function getIndiaDashboard(): Promise<IndiaDashboard> {
  return getJSON<IndiaDashboard>("/indicators/india", 3600);
}

/** Lifetime unique-visitor counter (homepage). */
export type Visits = { count: number };
export function getVisits(): Promise<Visits> {
  return getJSON<Visits>("/visits", 0);
}
export async function bumpVisits(): Promise<Visits> {
  const res = await fetch(`${API_BASE}/visits/hit`, { method: "POST", cache: "no-store" });
  if (!res.ok) throw new Error(`API ${res.status} for /visits/hit`);
  return res.json();
}

/** The election registry (past with results + upcoming) for the Elections module. */
export type Election = Schemas["Election"];
export function getElections(): Promise<Election[]> {
  return getJSON<Election[]>("/elections", 600);
}

/** Photos are served via the API proxy (upstream blocks cross-origin embedding). */
export function photoSrc(id: number, hasPhoto: string | null | undefined): string | null {
  return hasPhoto ? `${API_BASE}/persons/${id}/photo` : null;
}

/** Reply/debate PDFs are served via the API proxy — sansad.in/getFile is flaky (has 308-looped), so we
 * fetch + cache server-side and degrade gracefully instead of dumping users into a redirect loop. */
export function docSrc(kind: "question" | "debate", id: number): string {
  return `${API_BASE}/${kind}s/${id}/document`;
}

// ECI Files: the sourced ECI record (see docs/eci-files/SPEC.md §6-7, docs/eci-files/REDESIGN-SPEC.md
// §"Phase 2"). Gated behind noindex pages until launch — see the `robots` metadata on each `eci-files` route.
export type {
  EciEntry, EciEntryKind, EciEntryStatus, EciDatePrecision, EciCheckStatus, EciFigure, EciFilesLane,
  EciEntryPerson, EciResponseRef, EciCitation, EciTopicCount, EciPersonCount, EciTimelineCounts,
  EciLaneCount, EciCompactEntry, EciTimeline, EciCompactTimeline, EciHeadlineStat, EciSummaryCounts,
  EciSummary, EciDensityBucket, EciDensity, EciPersonSummary, EciPersonPage,
} from "@/types/eci-files";

export type EciTimelineOpts = {
  topic?: string; person?: string; status?: string; lane?: string; from?: string; to?: string; revalidate?: number;
};
/** The full-detail timeline (`/eci-files/entries`, a person's profile) — every field, including citations. */
export function getEciTimeline(opts: EciTimelineOpts = {}): Promise<EciTimeline> {
  return getJSON<EciTimeline>(`/eci-files/timeline${eciTimelineQuery(opts)}`, opts.revalidate ?? 3600);
}

/** The `fields=compact` timeline (the lane view's dots) — small enough that the first paint never pulls
 *  the whole record. The drawer fetches one full {@link EciEntry} on demand via `getEciEntry`. */
export function getEciTimelineCompact(opts: EciTimelineOpts = {}): Promise<EciCompactTimeline> {
  const qs = eciTimelineQuery(opts);
  const sep = qs ? "&" : "?";
  return getJSON<EciCompactTimeline>(`/eci-files/timeline${qs}${sep}fields=compact`, opts.revalidate ?? 900);
}

function eciTimelineQuery(opts: EciTimelineOpts): string {
  const q = new URLSearchParams();
  if (opts.topic) q.set("topic", opts.topic);
  if (opts.person) q.set("person", opts.person);
  if (opts.status) q.set("status", opts.status);
  if (opts.lane) q.set("lane", opts.lane);
  if (opts.from) q.set("from", opts.from);
  if (opts.to) q.set("to", opts.to);
  const qs = q.toString();
  return qs ? `?${qs}` : "";
}

/** The `/eci-files` front page's payload: headline stats, key moments, record-wide counts, freshness. */
export function getEciSummary(): Promise<EciSummary> {
  return getJSON<EciSummary>("/eci-files/summary", 900);
}

/** Monthly entry counts by lane, 2019 to today — the timeline's overview strip. Changes only when the
 *  record reloads, so it's cached longer than the (filterable) timeline itself. */
export function getEciDensity(): Promise<EciDensity> {
  return getJSON<EciDensity>("/eci-files/density", 3600);
}

export function getEciPeople(): Promise<EciPersonSummary[]> {
  return getJSON<EciPersonSummary[]>("/eci-files/people", 3600);
}

export async function getEciPerson(slug: string): Promise<EciPersonPage | null> {
  const res = await fetch(`${API_BASE}/eci-files/people/${encodeURIComponent(slug)}`, { next: { revalidate: 3600 } });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`API ${res.status} for /eci-files/people/${slug}`);
  return res.json();
}

export async function getEciEntry(id: string): Promise<EciEntry | null> {
  const res = await fetch(`${API_BASE}/eci-files/entries/${encodeURIComponent(id)}`, { next: { revalidate: 3600 } });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`API ${res.status} for /eci-files/entries/${id}`);
  return res.json();
}

// --- ECI Files phase 3 (numbers) ---
import type { EciStatesOverview, EciStatePage } from "@/types/eci-files";

export type {
  EciStage, EciRegionKind, EciExercise, EciNationalGroup, EciNationalMeasure, EciStageValue,
  EciStateMetric, EciStateMetrics, EciRegionSummary, EciNationalFigure, EciStatesOverview,
  EciStatePage, EciStateCount,
} from "@/types/eci-files";

export type EciTimelineOptsWithState = EciTimelineOpts & { state?: string };

/** Same as `eciTimelineQuery`, with an added `state=<slug>` term — kept separate rather than editing
 *  `EciTimelineOpts`/`eciTimelineQuery` in place, since phase 4 and 5 web workers touch this file in
 *  parallel (docs/eci-files/PHASE3-SPEC.md §3.8/§4). */
function eciTimelineQueryWithState(opts: EciTimelineOptsWithState): string {
  const base = eciTimelineQuery(opts);
  if (!opts.state) return base;
  return base ? `${base}&state=${encodeURIComponent(opts.state)}` : `?state=${encodeURIComponent(opts.state)}`;
}

/** The `fields=compact` timeline, optionally filtered to one region — state pages, and the lane
 *  timeline's own `state=` filter (PHASE3-SPEC.md §2.3, §3.6). */
export function getEciTimelineCompactByState(opts: EciTimelineOptsWithState = {}): Promise<EciCompactTimeline> {
  const qs = eciTimelineQueryWithState(opts);
  const sep = qs ? "&" : "?";
  return getJSON<EciCompactTimeline>(`/eci-files/timeline${qs}${sep}fields=compact`, opts.revalidate ?? 900);
}

/** All 36 regions with SIR/Special Revision stage figures, plus the cited national totals
 *  (`/eci-files/numbers`). */
export function getEciStates(): Promise<EciStatesOverview> {
  return getJSON<EciStatesOverview>("/eci-files/states", 3600);
}

/** One region's summary + notes, or null on 404 — same shape as {@link getEciPerson}. */
export async function getEciState(slug: string): Promise<EciStatePage | null> {
  const res = await fetch(`${API_BASE}/eci-files/states/${encodeURIComponent(slug)}`, { next: { revalidate: 3600 } });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`API ${res.status} for /eci-files/states/${slug}`);
  return res.json();
}
// --- end phase 3 ---

// --- ECI Files phase 4 (people) ---
import type { EciSelections as _EciSelections } from "@/types/eci-files";
export type {
  EciPersonGroup, EciPhoto, EciStatusCounts, EciEntryRef, EciSelectionPart, EciSelectionMethod,
  EciSelectionRegimeKey, EciSelectionAppointee, EciSelectionMember, EciSelectionSearch, EciSelectionDissent,
  EciSelection, EciSelectionRegime, EciDeparture, EciSelections, EciPersonDetail,
} from "@/types/eci-files";

/** `/eci-files/selections` — the eight selections, three regimes and six departures behind them. */
export function getEciSelections(): Promise<_EciSelections> {
  return getJSON<_EciSelections>("/eci-files/selections", 3600);
}
// --- end phase 4 ---

// --- ECI Files phase 5 (views) ---
// /eci-files/objections, /answers, /rules(+diff) and /courts(+case). Types are hand-written in
// src/types/eci-files.ts (§4 of PHASE5-SPEC.md) — the backend worker's `schemas.py` isn't written yet.
import type {
  EciEntryCard, EciPersonWithPhoto, EciObjection, EciObjectionPersonCount, EciObjectionsPage,
  EciRelatedRef, EciAnswerRow, EciAnswersCounts, EciUnpairedResponse, EciAnswersPage, EciAnswersView,
  EciTextStatus, EciRuleDiffRef, EciRuleRow, EciRulesPage, EciRuleDiff,
  EciCaseShortStatus, EciCaseRole, EciCaseSummary, EciCourtsPage, EciCaseItem, EciCaseParties, EciCasePage,
  EciEntryContext, EciEntryDetail,
} from "@/types/eci-files";
export type {
  EciEntryCard, EciPersonWithPhoto, EciObjection, EciObjectionPersonCount, EciObjectionsPage,
  EciRelatedRef, EciAnswerRow, EciAnswersCounts, EciUnpairedResponse, EciAnswersPage, EciAnswersView,
  EciTextStatus, EciRuleDiffRef, EciRuleRow, EciRulesPage, EciRuleDiff,
  EciCaseShortStatus, EciCaseRole, EciCaseSummary, EciCourtsPage, EciCaseItem, EciCaseParties, EciCasePage,
  EciEntryContext, EciEntryDetail,
};

/** `GET /eci-files/entries/{id}`, typed for the richer phase-5 shape (`context`). Kept alongside the
 *  existing {@link getEciEntry} rather than changing its return type in place — `api.ts` is a hotspot
 *  three phases append to, and `getEciEntry` is called by pre-phase-5 code outside this block. Once the
 *  backend ships `EciEntryDetail` from the same route, {@link getEciEntry}'s return type can just widen to
 *  match and this can be dropped. */
export async function getEciEntryDetail(id: string): Promise<EciEntryDetail | null> {
  const res = await fetch(`${API_BASE}/eci-files/entries/${encodeURIComponent(id)}`, { next: { revalidate: 3600 } });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`API ${res.status} for /eci-files/entries/${id}`);
  return res.json();
}

export function getEciObjections(): Promise<EciObjectionsPage> {
  return getJSON<EciObjectionsPage>("/eci-files/objections", 3600);
}

export function getEciAnswers(view: EciAnswersView = "all"): Promise<EciAnswersPage> {
  const qs = view === "all" ? "" : `?view=${view}`;
  return getJSON<EciAnswersPage>(`/eci-files/answers${qs}`, 3600);
}

export function getEciRules(): Promise<EciRulesPage> {
  return getJSON<EciRulesPage>("/eci-files/rules", 3600);
}

export async function getEciRuleDiff(id: string): Promise<EciRuleDiff | null> {
  const res = await fetch(`${API_BASE}/eci-files/rules/diffs/${encodeURIComponent(id)}`, { next: { revalidate: 3600 } });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`API ${res.status} for /eci-files/rules/diffs/${id}`);
  return res.json();
}

export function getEciCourts(): Promise<EciCourtsPage> {
  return getJSON<EciCourtsPage>("/eci-files/courts", 3600);
}

export async function getEciCase(slug: string): Promise<EciCasePage | null> {
  const res = await fetch(`${API_BASE}/eci-files/courts/${encodeURIComponent(slug)}`, { next: { revalidate: 3600 } });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`API ${res.status} for /eci-files/courts/${slug}`);
  return res.json();
}
// --- end phase 5 ---
