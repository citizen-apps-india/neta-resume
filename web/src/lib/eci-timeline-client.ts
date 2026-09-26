// Browser-side helpers for the reworked /eci-files/timeline page: fetches through the same-origin proxy
// (src/app/api/eci-files/*), plus the pure grouping/filtering/clustering logic the page's client
// component (TimelineView) needs. Kept out of lib/eci-files.ts (a hotspot other workers append to) and
// out of lib/api.ts (server-only fetchers, since NETA_API_BASE never reaches the browser).

import type { EciCompactEntry, EciCompactTimeline, EciEntryDetail, EciFilesLane } from "@/types/eci-files";
import { ECI_RECORD_END_MONTH, ECI_RECORD_START_MONTH, monthRange, toMonthKey } from "@/lib/eci-files";

// ---- fetching (client-side, no full page reload) ----

export type EciTimelineWindowOpts = { topic?: string; person?: string; from: string; to: string };

/** Fetches the compact timeline for a window/topic/person combination through `/api/eci-files/timeline`.
 *  Called on every window drag, month click and topic/person change so the timeline page never falls
 *  back to a server round trip or a full reload. */
export async function fetchEciTimelineWindow(opts: EciTimelineWindowOpts): Promise<EciCompactTimeline> {
  const q = new URLSearchParams();
  if (opts.topic) q.set("topic", opts.topic);
  if (opts.person) q.set("person", opts.person);
  q.set("from", opts.from);
  q.set("to", opts.to);
  const res = await fetch(`/api/eci-files/timeline?${q.toString()}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`timeline ${res.status}`);
  return res.json();
}

/** Fetches one full entry (citations, context) for the in-place expanded card. `null` on a real 404. */
export async function fetchEciEntryDetailClient(id: string): Promise<EciEntryDetail | null> {
  const res = await fetch(`/api/eci-files/entries/${encodeURIComponent(id)}`, { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`entry ${res.status}`);
  return res.json();
}

// ---- filtering (lane chips / checked-only / search — all client-side, no fetch) ----

export interface EciTimelineFilter {
  lanes: Set<EciFilesLane>;
  checkedOnly: boolean;
  query: string;
}

/** Search covers title and named people only — `states` isn't on the compact shape (REDESIGN-SPEC's
 *  `fields=compact` drops it to keep the first paint light), so the control bar doesn't claim to search it. */
export function filterEntries(entries: EciCompactEntry[], filter: EciTimelineFilter): EciCompactEntry[] {
  const q = filter.query.trim().toLowerCase();
  return entries.filter((e) => {
    if (!filter.lanes.has(e.lane)) return false;
    if (filter.checkedOnly && e.check_status !== "checked") return false;
    if (q) {
      const hay = `${e.title} ${e.people.map((p) => p.name).join(" ")}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

// ---- same-day + duplicate folding ----

const STOPWORDS = new Set(["the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "at", "by", "with", "from", "is", "are", "as", "its", "over"]);

function titleTokens(title: string): Set<string> {
  return new Set(
    title
      .toLowerCase()
      .replace(/['’]/g, "")
      .replace(/[^a-z0-9\s]/g, " ")
      .split(/\s+/)
      .filter((t) => t.length > 2 && !STOPWORDS.has(t)),
  );
}

function jaccard(a: Set<string>, b: Set<string>): number {
  if (a.size === 0 || b.size === 0) return 0;
  let inter = 0;
  for (const t of a) if (b.has(t)) inter++;
  return inter / (a.size + b.size - inter);
}

/** Same-day title overlap above this fraction reads as the same record kept twice. Conservative on
 *  purpose: a missed duplicate is one extra row; a wrong merge would hide one. `data/eci_files/merges.json`
 *  is the curated, already-applied version of this same judgement for cross-area duplicates the loader
 *  found; this catches same-day near-duplicates the API still returns as separate entries. */
const DUPLICATE_THRESHOLD = 0.6;

export interface EciEntryCluster {
  kept: EciCompactEntry;
  extra: EciCompactEntry[];
}

/** Groups same-day entries whose titles look like the same record recorded more than once. Order is
 *  preserved (the API returns date-ascending, then id), so `kept` is always the first of the group seen. */
export function clusterDuplicates(dayEntries: EciCompactEntry[]): EciEntryCluster[] {
  const groups: { entries: EciCompactEntry[]; tokens: Set<string>[] }[] = [];
  for (const e of dayEntries) {
    const tokens = titleTokens(e.title);
    const group = groups.find((g) => g.tokens.some((t) => jaccard(t, tokens) >= DUPLICATE_THRESHOLD));
    if (group) {
      group.entries.push(e);
      group.tokens.push(tokens);
    } else {
      groups.push({ entries: [e], tokens: [tokens] });
    }
  }
  return groups.map((g) => ({ kept: g.entries[0], extra: g.entries.slice(1) }));
}

/** A day this busy folds into one "N entries on this day" row instead of N rows. */
export const DAY_FOLD_THRESHOLD = 5;

export interface EciDayGroup {
  /** null only for the "Undated" bucket. */
  date: string | null;
  rawCount: number;
  clusters: EciEntryCluster[];
}

export interface EciMonthBlock {
  key: string;
  label: string;
  total: number;
  days: EciDayGroup[];
}

const MONTHS_FULL = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

/** Already date-ascending compact entries -> month blocks, each carrying its day groups (clustered for
 *  duplicate folding). A day whose `rawCount` is at or above {@link DAY_FOLD_THRESHOLD} is the "N entries
 *  on this day" fold; every other day renders one row per cluster. */
export function buildMonthBlocks(entries: EciCompactEntry[]): EciMonthBlock[] {
  const byDate = new Map<string, EciCompactEntry[]>();
  const dateOrder: string[] = [];
  for (const e of entries) {
    const key = e.date ?? "undated";
    if (!byDate.has(key)) {
      byDate.set(key, []);
      dateOrder.push(key);
    }
    byDate.get(key)!.push(e);
  }

  const monthOrder: string[] = [];
  const monthDays = new Map<string, EciDayGroup[]>();
  const monthLabel = new Map<string, string>();

  for (const dateKey of dateOrder) {
    const dayEntries = byDate.get(dateKey)!;
    const first = dayEntries[0];
    let monthKey: string;
    let label: string;
    const d = first.date ? new Date(`${first.date}T00:00:00Z`) : null;
    if (!d || isNaN(d.getTime())) {
      monthKey = "undated";
      label = "Undated";
    } else if (first.date_precision === "year") {
      monthKey = String(d.getUTCFullYear());
      label = monthKey;
    } else {
      monthKey = `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
      label = `${MONTHS_FULL[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
    }
    if (!monthDays.has(monthKey)) {
      monthDays.set(monthKey, []);
      monthOrder.push(monthKey);
      monthLabel.set(monthKey, label);
    }
    monthDays.get(monthKey)!.push({
      date: dateKey === "undated" ? null : dateKey,
      rawCount: dayEntries.length,
      clusters: clusterDuplicates(dayEntries),
    });
  }

  return monthOrder.map((key) => {
    const days = monthDays.get(key)!;
    return { key, label: monthLabel.get(key)!, days, total: days.reduce((n, d) => n + d.rawCount, 0) };
  });
}

// ---- the whole-record month window (heat map / month strip / "jump to" centring) ----

export const ECI_RECORD_MONTHS: string[] = monthRange(ECI_RECORD_START_MONTH, ECI_RECORD_END_MONTH);

function monthKeyBounds(key: string): { from: string; to: string } {
  const [y, m] = key.split("-").map(Number);
  const last = new Date(Date.UTC(y, m, 0)).getUTCDate();
  return { from: `${key}-01`, to: `${key}-${String(last).padStart(2, "0")}` };
}

/** The default ~6-month window centred on one month key, clamped to the record's span — the same shape
 *  as `defaultEciWindow()` but centred anywhere, for a heat-map month click, a month-strip tap or a
 *  "jump to a key moment" link landing outside the currently loaded window. */
export function windowAroundMonth(monthKey: string): { from: string; to: string } {
  const idx = ECI_RECORD_MONTHS.indexOf(monthKey);
  const centre = idx === -1 ? ECI_RECORD_MONTHS.length - 1 : idx;
  const startIdx = Math.max(0, centre - 3);
  const endIdx = Math.min(ECI_RECORD_MONTHS.length - 1, centre + 2);
  return { from: monthKeyBounds(ECI_RECORD_MONTHS[startIdx]).from, to: monthKeyBounds(ECI_RECORD_MONTHS[endIdx]).to };
}

/** An exact month-to-month range (a heat-map drag), each end clamped to that month's first/last day. */
export function windowFromMonthRange(startKey: string, endKey: string): { from: string; to: string } {
  return { from: monthKeyBounds(startKey).from, to: monthKeyBounds(endKey).to };
}

export function windowAroundDate(dateIso: string): { from: string; to: string } {
  return windowAroundMonth(toMonthKey(new Date(`${dateIso}T00:00:00Z`)));
}

/** "January 2026" / "January – February 2026" / "November 2025 – February 2026" — the period card's
 *  heading for the current window. */
export function periodLabel(from: string, to: string): string {
  const f = new Date(`${from}T00:00:00Z`);
  const t = new Date(`${to}T00:00:00Z`);
  const fLabel = `${MONTHS_FULL[f.getUTCMonth()]} ${f.getUTCFullYear()}`;
  const tLabel = `${MONTHS_FULL[t.getUTCMonth()]} ${t.getUTCFullYear()}`;
  if (fLabel === tLabel) return fLabel;
  if (f.getUTCFullYear() === t.getUTCFullYear()) return `${MONTHS_FULL[f.getUTCMonth()]} – ${tLabel}`;
  return `${fLabel} – ${tLabel}`;
}
