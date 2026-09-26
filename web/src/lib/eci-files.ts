// Display helpers specific to ECI Files: date precision, status-chip tokens, and year/month grouping
// for the timeline. Kept separate from lib/format.ts because this vocabulary (documented/reported/
// claim/response, day/month/year precision) belongs to this one source.

import type {
  EciCareerLine, EciDensityBucket, EciEntry, EciEntryStatus, EciFilesLane, EciTenure,
} from "@/types/eci-files";
// ECI Files phase 5 (views): types for the new helpers appended at the end of this file.
import type { EciEntryRef, EciTextStatus, EciCaseRole, EciCaseShortStatus } from "@/types/eci-files";

/** Format a date honouring its recorded precision: "24 Jun 2025" (day), "Jul 2026" (month), "2019" (year).
 *  Missing or unparsable dates render "—", per house rule. */
export function formatEciDate(date: string | null, precision: string): string {
  if (!date) return "—";
  const d = new Date(`${date}T00:00:00Z`);
  if (isNaN(d.getTime())) return "—";
  if (precision === "year") return String(d.getUTCFullYear());
  if (precision === "month") {
    return d.toLocaleDateString("en-IN", { year: "numeric", month: "short", timeZone: "UTC" });
  }
  return d.toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" });
}

export interface EciStatusMeta {
  label: string;
  /** The role token itself (e.g. "var(--eci-doc)") — the one colour components are allowed to use for
   *  this status (REDESIGN-SPEC §"Identity": "Components use only those tokens"). */
  token: string;
  fg: string;
  bg: string;
  bd: string;
}

/** Status -> the four ECI trust-colour role tokens (`--eci-doc/-report/-claim/-response`, added to
 *  `globals.css` for both themes per REDESIGN-SPEC §"Identity"). Each status reads as a distinct colour,
 *  never a verdict — "documented" is a provenance fact (we opened a primary document), not a claim that the
 *  underlying event is true. `bg`/`bd` are derived from the token with `color-mix`, never a second hex, so
 *  the token stays the single source of that colour. */
export const ECI_STATUS_META: Record<EciEntryStatus, EciStatusMeta> = {
  documented: {
    label: "Document", token: "var(--eci-doc)",
    fg: "var(--eci-doc)", bg: "color-mix(in srgb, var(--eci-doc) 12%, var(--card2))", bd: "color-mix(in srgb, var(--eci-doc) 40%, var(--rule))",
  },
  reported: {
    label: "Reported", token: "var(--eci-report)",
    fg: "var(--eci-report)", bg: "color-mix(in srgb, var(--eci-report) 12%, var(--card2))", bd: "color-mix(in srgb, var(--eci-report) 40%, var(--rule))",
  },
  claim: {
    label: "Claim", token: "var(--eci-claim)",
    fg: "var(--eci-claim)", bg: "color-mix(in srgb, var(--eci-claim) 12%, var(--card2))", bd: "color-mix(in srgb, var(--eci-claim) 40%, var(--rule))",
  },
  response: {
    label: "Response", token: "var(--eci-response)",
    fg: "var(--eci-response)", bg: "color-mix(in srgb, var(--eci-response) 14%, var(--card2))", bd: "color-mix(in srgb, var(--eci-response) 45%, var(--rule))",
  },
};

export function eciStatusMeta(status: EciEntryStatus): EciStatusMeta {
  return ECI_STATUS_META[status] ?? { label: status, token: "var(--muted)", fg: "var(--muted)", bg: "var(--sunken)", bd: "var(--border2)" };
}

/** Lane -> display label, in the fixed row order the timeline always renders them in
 *  (REDESIGN-SPEC §"Lanes": "Commission, Inside the Commission, Courts, Claims, Responses"). */
export const ECI_LANE_META: Record<EciFilesLane, { label: string; short: string }> = {
  commission: { label: "Commission", short: "Commission" },
  inside: { label: "Inside the Commission", short: "Inside" },
  courts: { label: "Courts", short: "Courts" },
  claims: { label: "Claims", short: "Claims" },
  responses: { label: "Responses", short: "Responses" },
};

export const ECI_LANE_ORDER: EciFilesLane[] = ["commission", "inside", "courts", "claims", "responses"];

export function eciLaneLabel(lane: EciFilesLane): string {
  return ECI_LANE_META[lane]?.label ?? lane;
}

const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export interface EciMonthGroup {
  /** null for entries whose precision is "year" (no month on record) — rendered without a month heading. */
  label: string | null;
  entries: EciEntry[];
}

export interface EciYearGroup {
  year: string;
  months: EciMonthGroup[];
}

/** Group entries (already date-ascending from the API) into year -> month buckets, preserving order.
 *  A "year"-precision entry has no month, and lands in its own unlabelled bucket rather than being
 *  guessed into a month. Entries with no date at all group under "Undated". */
export function groupEciTimeline(entries: EciEntry[]): EciYearGroup[] {
  const order: string[] = [];
  const years = new Map<string, { monthOrder: string[]; months: Map<string, EciEntry[]> }>();

  for (const entry of entries) {
    const d = entry.date ? new Date(`${entry.date}T00:00:00Z`) : null;
    const valid = d !== null && !isNaN(d.getTime());
    const yearKey = valid ? String(d!.getUTCFullYear()) : "Undated";
    const monthKey = valid && entry.date_precision !== "year" ? MONTH_NAMES[d!.getUTCMonth()] : "—";

    let bucket = years.get(yearKey);
    if (!bucket) {
      bucket = { monthOrder: [], months: new Map() };
      years.set(yearKey, bucket);
      order.push(yearKey);
    }
    if (!bucket.months.has(monthKey)) {
      bucket.monthOrder.push(monthKey);
      bucket.months.set(monthKey, []);
    }
    bucket.months.get(monthKey)!.push(entry);
  }

  return order.map((year) => {
    const bucket = years.get(year)!;
    return {
      year,
      months: bucket.monthOrder.map((label) => ({
        label: label === "—" ? null : label,
        entries: bucket.months.get(label)!,
      })),
    };
  });
}

/** Look up an entry's title by id within a flat list — used to caption a response with what it answers. */
export function titleOf(entries: EciEntry[], id: string | null): string | null {
  if (!id) return null;
  return entries.find((e) => e.id === id)?.title ?? null;
}

/** "term_start" -> "Term start" — a readable label for a profile-entry detail key. `details` is a free-form
 *  jsonb bag (postings, roles — see BRIEF.md's officials-profile rule), so this is deliberately generic. */
function humanizeKey(key: string): string {
  const words = key.replace(/[_-]+/g, " ").trim();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export interface EciDetailLine {
  label: string;
  value: string;
}

/** The scalar entries of a profile's `details` bag, rendered as career lines. Nested objects/arrays are
 *  left out — their shape isn't part of the public contract, only the scalar facts are. */
export function detailLines(details: Record<string, unknown>): EciDetailLine[] {
  return Object.entries(details)
    .filter(([k, v]) => !k.endsWith("url") && v !== null && v !== undefined && (typeof v === "string" || typeof v === "number" || typeof v === "boolean"))
    .map(([k, v]) => ({ label: humanizeKey(k), value: String(v) }));
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "2024-03-15" -> "Mar 2024", "2019" -> "2019"; anything unparseable is shown as given. */
export function formatLooseDate(value?: string | null): string {
  if (!value) return "—";
  const m = /^(\d{4})(?:-(\d{2}))?/.exec(value);
  if (!m) return value;
  return m[2] ? `${MONTHS[Number(m[2]) - 1] ?? ""} ${m[1]}`.trim() : m[1];
}

/** One line per office held: "Election Commissioner, Mar 2024 – Feb 2025". */
export function formatTenure(tenure: EciTenure[] | undefined | null): string[] {
  return (tenure ?? []).map((t) => {
    const span = `${formatLooseDate(t.from)} – ${t.to ? formatLooseDate(t.to) : "present"}`;
    return t.office ? `${t.office}, ${span}` : span;
  });
}

/** The career lines of a person entry's `details.career`, dropping anything malformed. */
export function careerLines(details: Record<string, unknown>): EciCareerLine[] {
  const raw = details.career;
  if (!Array.isArray(raw)) return [];
  return raw.filter((c): c is EciCareerLine => typeof c === "object" && c !== null && typeof (c as EciCareerLine).post === "string");
}

// ---- timeline overview strip + lane window (web/src/app/eci-files/timeline) -------------------------

/** The record's fixed span (REDESIGN-SPEC §"Overview": "A density strip across 2019 to 2026 by month") —
 *  the x-axis never grows or shrinks with the data, so the strip reads the same shape on every visit. */
export const ECI_RECORD_START_MONTH = "2019-01";
export const ECI_RECORD_END_MONTH = "2026-09";

/** UTC first-of-month `Date` for a "YYYY-MM" key. */
function monthDate(key: string): Date {
  const [y, m] = key.split("-").map(Number);
  return new Date(Date.UTC(y, (m || 1) - 1, 1));
}

/** `Date` -> "YYYY-MM", in UTC (dates on the record are stored as plain calendar days, not instants). */
export function toMonthKey(d: Date): string {
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
}

/** Every "YYYY-MM" from `start` to `end` inclusive, ascending. */
export function monthRange(start: string, end: string): string[] {
  const out: string[] = [];
  let d = monthDate(start);
  const last = monthDate(end);
  while (d.getTime() <= last.getTime()) {
    out.push(toMonthKey(d));
    d = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 1));
  }
  return out;
}

/** "2025-08" -> "Aug 2025". */
export function formatMonthKey(key: string): string {
  const [y, m] = key.split("-").map(Number);
  return `${MONTHS[(m || 1) - 1] ?? ""} ${y}`;
}

export interface EciMonthTotal {
  month: string;
  total: number;
  byLane: Record<EciFilesLane, number>;
}

/** Density buckets (one row per month+lane) -> one row per month, every month in the record's fixed span
 *  present (zero-filled), each carrying its per-lane breakdown for the tooltip. */
export function densityByMonth(buckets: EciDensityBucket[]): EciMonthTotal[] {
  const byMonth = new Map<string, Record<EciFilesLane, number>>();
  for (const b of buckets) {
    let row = byMonth.get(b.month);
    if (!row) {
      row = { commission: 0, inside: 0, courts: 0, claims: 0, responses: 0 };
      byMonth.set(b.month, row);
    }
    row[b.lane] = (row[b.lane] ?? 0) + b.count;
  }
  return monthRange(ECI_RECORD_START_MONTH, ECI_RECORD_END_MONTH).map((month) => {
    const byLane = byMonth.get(month) ?? { commission: 0, inside: 0, courts: 0, claims: 0, responses: 0 };
    return { month, byLane, total: Object.values(byLane).reduce((a, b) => a + b, 0) };
  });
}

/** The default ~6-month lane-timeline window (REDESIGN-SPEC §"Overview": "the web asks for about 6 months
 *  at a time") ending "now", clamped to the record's start. `now` is injected for deterministic tests/SSR. */
export function defaultEciWindow(now: Date = new Date()): { from: string; to: string } {
  const to = now.toISOString().slice(0, 10);
  const start = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() - 5, 1));
  const floor = monthDate(ECI_RECORD_START_MONTH);
  const from = (start.getTime() < floor.getTime() ? floor : start).toISOString().slice(0, 10);
  return { from, to };
}

/** Builds `/eci-files/timeline?...&entry=<id>`, carrying over the current lane/topic/person/window
 *  (`preserve`) so following a "replying to" / "responses" link inside the drawer doesn't reset the page
 *  back to its default filters — the drawer content is server-rendered, so it can't read `useSearchParams`
 *  itself the way the client `EntryDrawer` shell that opens/closes it does. */
export function eciEntryHref(id: string, preserve: Record<string, string | undefined> = {}): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(preserve)) if (v) p.set(k, v);
  p.set("entry", id);
  return `/eci-files/timeline?${p.toString()}`;
}

/** Where a date falls between two ISO bounds, as a 0–1 fraction — for positioning a dot along a lane's
 *  horizontal axis. Dates outside the window clamp to the nearest edge rather than disappearing. */
export function dateFraction(date: string, from: string, to: string): number {
  const t = new Date(`${date}T00:00:00Z`).getTime();
  const a = new Date(`${from}T00:00:00Z`).getTime();
  const b = new Date(`${to}T00:00:00Z`).getTime();
  if (b <= a) return 0;
  return Math.min(1, Math.max(0, (t - a) / (b - a)));
}

// --- ECI Files phase 5 (views) ---
// Helpers for /eci-files/objections, /answers, /rules(+diff) and /courts(+case). `initials()` is phase
// 4's helper (redefined here only because phase 4 hasn't landed on this branch yet — see PersonAvatar).

/** "Sukhbir Singh Sandhu" -> "SS" — first letter of the first and last word. Phase 4's shape. */
export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

/** Builds an entry link that stays on `basePath` (the page you're already reading), instead of always
 *  sending the reader to `/eci-files/timeline` the way {@link eciEntryHref} does. Phase 4's spec adds a
 *  `basePath` parameter to `eciEntryHref` itself; until that lands, phase 5's new pages use this instead,
 *  so a later rebase can fold the two call sites back into one function. */
export function eciEntryHrefIn(basePath: string, id: string, preserve: Record<string, string | undefined> = {}): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(preserve)) if (v) p.set(k, v);
  p.set("entry", id);
  return `${basePath}?${p.toString()}`;
}

export type EciFollowedBySegment =
  | { kind: "text"; text: string }
  | { kind: "entry"; id: string; ref: EciEntryRef | null }
  | { kind: "objection"; n: number };

/** Splits an objection's `followed_by` prose into plain text plus the two token kinds it can contain:
 *  `(entry-id)` (an area-prefixed id — becomes a "(see entry)" drawer link) and `(objection N)` (becomes
 *  a same-page anchor link). Pure, so it's testable without a DOM. */
export function linkifyFollowedBy(text: string | null, refs: EciEntryRef[]): EciFollowedBySegment[] {
  if (!text) return [];
  const byId = new Map(refs.map((r) => [r.id, r]));
  const pattern = /\((objection\s+(\d+)|[a-z0-9][a-z0-9-]*)\)/gi;
  const out: EciFollowedBySegment[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = pattern.exec(text))) {
    if (m.index > last) out.push({ kind: "text", text: text.slice(last, m.index) });
    const objMatch = /^objection\s+(\d+)$/i.exec(m[1]);
    if (objMatch) {
      out.push({ kind: "objection", n: Number(objMatch[1]) });
    } else if (byId.has(m[1])) {
      out.push({ kind: "entry", id: m[1], ref: byId.get(m[1]) ?? null });
    } else {
      out.push({ kind: "text", text: m[0] });
    }
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push({ kind: "text", text: text.slice(last) });
  return out;
}

/** `/eci-files/rules` and `/eci-files/rules/[diff]` — the label a reader sees for each of the three text
 *  statuses (PHASE5-SPEC §5). */
export const ECI_TEXT_STATUS_LABEL: Record<EciTextStatus, string> = {
  verbatim: "Verbatim from the document",
  "quoted in reporting": "Wording as quoted in news reports",
  "paraphrased from reporting": "Paraphrased from news reports: not the document's wording",
};

/** The short form used on list rows and badges, per §6.4: "Verbatim", "Quoted in reports", "Paraphrased". */
export const ECI_TEXT_STATUS_SHORT: Record<EciTextStatus, string> = {
  verbatim: "Verbatim",
  "quoted in reporting": "Quoted in reports",
  "paraphrased from reporting": "Paraphrased",
};

/** `/eci-files/courts` — case status chip text (never colour alone). */
export const ECI_CASE_STATUS_LABEL: Record<EciCaseShortStatus, string> = {
  pending: "Pending",
  disposed: "Decided",
  referred: "Pending · referred to the Chief Justice",
};

/** `/eci-files/courts/[case]` — the role chip text for one recorded step. */
export const ECI_CASE_ROLE_LABEL: Record<EciCaseRole, string> = {
  order: "Order",
  judgment: "Judgment",
  hearing: "Hearing",
  filing: "Filing",
  listing: "Listing",
  recusal: "Recusal",
  compliance: "Commission acts on order",
  related: "Related",
};
// --- end phase 5 ---
