// Typed client for the FastAPI read layer. Called from server components (no DB creds in browser).
// The types below are ALIASES over the OpenAPI-generated contract in src/types/api.ts — the single
// source of truth is api/neta_api/schemas.py. After changing the API schema, run `npm run codegen`
// (with the API running) to refresh src/types/api.ts; these aliases then pick the changes up.

import type { components } from "@/types/api";

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
  jurisdiction?: string; party?: string; cases?: string; q?: string; theme?: string; sort?: string; revalidate?: number;
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
  if (opts.sort) q.set("sort", opts.sort);
  const res = await fetch(`${API_BASE}/persons?${q.toString()}`, { next: { revalidate: opts.revalidate ?? 3600 } });
  if (!res.ok) throw new Error(`API ${res.status} for /persons`);
  const items = (await res.json()) as PersonSummary[];
  const total = Number(res.headers.get("x-total-count") ?? items.length);
  return { items, total };
}

/** Dropdown option lists (party / state / house, each with a count) for a browse scope. */
export type FacetCount = { value: string; count: number };
export type Facets = { parties: FacetCount[]; states: FacetCount[]; houses: FacetCount[]; themes: FacetCount[] };
export function getFacets(
  opts: { house?: string; state?: string; jurisdiction?: string } = {},
): Promise<Facets> {
  const q = new URLSearchParams();
  if (opts.house) q.set("house", opts.house);
  if (opts.state) q.set("state", opts.state);
  if (opts.jurisdiction) q.set("jurisdiction", opts.jurisdiction);
  return getJSON<Facets>(`/persons/facets?${q.toString()}`, 3600);
}

export function searchPersons(q: string): Promise<PersonSummary[]> {
  return getJSON<PersonSummary[]>(`/search?q=${encodeURIComponent(q)}`, 0);
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
export function getParliamentStats(): Promise<ParliamentStats> {
  return getJSON<ParliamentStats>("/parliament/stats", 3600);
}
export function getParliamentMinistries(): Promise<MinistryCount[]> {
  return getJSON<MinistryCount[]>("/parliament/ministries", 3600);
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
export type SearchRecordsOpts = { q: string; kind?: string; theme?: string; limit?: number; offset?: number };
/** A page of matching questions/debates plus the total match count (from X-Total-Count). */
export async function searchRecords(opts: SearchRecordsOpts): Promise<{ items: RecordHit[]; total: number }> {
  const p = new URLSearchParams();
  p.set("q", opts.q);
  if (opts.kind) p.set("kind", opts.kind);
  if (opts.theme) p.set("theme", opts.theme);
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
export function getParliamentTrends(): Promise<Trends> {
  return getJSON<Trends>("/parliament/trends", 3600);
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
