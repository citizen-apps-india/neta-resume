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

// `detailLines()` (a generic dump of every scalar in a profile's `details` bag) rendered `born` on five
// profiles — a date of birth, which is a personal detail this record does not carry (PHASE4-SPEC.md §2.4).
// Deleted rather than fixed: `CareerTimeline`'s `careerTimeline()` (below, phase 4 block) replaces it with
// an explicit allowlist (`service`, `education`, `tenure_end`) that can never grow a new leak by accident.

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
export function eciEntryHref(id: string, preserve: Record<string, string | undefined> = {}, basePath = "/eci-files/timeline"): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(preserve)) if (v) p.set(k, v);
  p.set("entry", id);
  return `${basePath}?${p.toString()}`;
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

// --- ECI Files phase 4 (people) ---
// `/eci-files/people`, `/eci-files/people/[slug]` and `/eci-files/selections` (PHASE4-SPEC.md §§1-4).
// A second `import` on the same module is deliberate: it keeps this block a self-contained append that
// never touches the hotspot's existing top-of-file import line.
import type { EciPersonGroup, EciPhoto, EciSelectionRegime } from "@/types/eci-files";

/** The shared x-axis for every tenure bar on every ECI Files people page (PHASE4-SPEC.md §1.2): fixed at
 *  2019-01-01, running to today. Computed once at module load — good enough for a display axis that only
 *  needs day precision, not per-request freshness. */
export const ECI_TENURE_AXIS: { from: string; to: string } = {
  from: "2019-01-01",
  to: new Date().toISOString().slice(0, 10),
};

const ECI_CEC_OFFICE_RE = /^Chief Election Commissioner$/;
const ECI_EC_OFFICE_RE = /^Election Commissioner$/;
/** A posting counts "at the Commission" for the career rail's ink-coloured segments (§2.4: "post names
 *  ECI / Election Commission / Chief Electoral Officer"). */
const ECI_AT_COMMISSION_RE = /\b(ECI|Election Commission|Chief Electoral Officer)\b/i;

export type EciTenureSegmentKind = "ec" | "cec" | "other";

export interface EciTenureSegment {
  office: string;
  kind: EciTenureSegmentKind;
  /** Fraction [0,1] of the axis width — already clamped to the axis bounds. */
  x0: number;
  x1: number;
  /** The segment started before the axis (drawn with a `◂ from …` marker instead of a hard left edge). */
  clippedStart: boolean;
  /** `to` is null — the segment runs to today and ends in an open notch, not a rounded corner. */
  openEnd: boolean;
  from: string;
  to: string | null;
}

/** One tenure's segments as bar geometry, shared by `TenureBar` and `CommissionTenureChart` so both draw
 *  the exact same shape on the exact same axis (PHASE4-SPEC.md §2.5). A tenure with no `from` (only a
 *  `to`) draws no bar segment here — `TenureBar` renders that as a 2px tick instead. */
export function tenureSegments(
  tenure: EciTenure[] | undefined | null,
  axis: { from: string; to: string } = ECI_TENURE_AXIS,
): EciTenureSegment[] {
  return (tenure ?? [])
    .filter((t): t is EciTenure & { from: string } => typeof t.from === "string" && t.from.length > 0)
    .map((t) => {
      const office = t.office ?? "";
      const kind: EciTenureSegmentKind = ECI_CEC_OFFICE_RE.test(office) ? "cec" : ECI_EC_OFFICE_RE.test(office) ? "ec" : "other";
      const to = t.to ?? null;
      const clippedStart = t.from < axis.from;
      const openEnd = to === null;
      const x0 = dateFraction(clippedStart ? axis.from : t.from, axis.from, axis.to);
      const x1 = dateFraction(to ?? axis.to, axis.from, axis.to);
      return { office, kind, x0, x1, clippedStart, openEnd, from: t.from, to };
    });
}

/** One day-to-day run of how many commissioners were in office at once (PHASE4-SPEC.md §1.2, "Members in
 *  office" strip) — a sweep over every commission-office interval, clamped to `axis`, collapsed into runs
 *  of constant count. `intervals` is every commissioner's EC/CEC tenure span; overlapping spans (a
 *  hand-over day) are expected and are what makes the count go to 2 or back to 1. */
export function membersInOffice(
  intervals: { from: string; to: string | null }[],
  axis: { from: string; to: string } = ECI_TENURE_AXIS,
): { from: string; to: string; count: number }[] {
  const addDays = (iso: string, days: number): string => {
    const d = new Date(`${iso}T00:00:00Z`);
    d.setUTCDate(d.getUTCDate() + days);
    return d.toISOString().slice(0, 10);
  };
  const clamped = intervals
    .map((iv) => ({
      from: iv.from < axis.from ? axis.from : iv.from,
      to: (iv.to ?? axis.to) > axis.to ? axis.to : (iv.to ?? axis.to),
    }))
    .filter((iv) => iv.from <= iv.to);

  const points = new Set<string>([axis.from, axis.to]);
  for (const iv of clamped) {
    points.add(iv.from);
    if (iv.to < axis.to) points.add(addDays(iv.to, 1));
  }
  const bounds = Array.from(points).filter((d) => d >= axis.from && d <= axis.to).sort();

  const runs: { from: string; to: string; count: number }[] = [];
  for (let i = 0; i < bounds.length; i++) {
    const segFrom = bounds[i];
    if (segFrom > axis.to) break;
    const segTo = i + 1 < bounds.length ? addDays(bounds[i + 1], -1) : axis.to;
    const count = clamped.filter((iv) => iv.from <= segFrom && iv.to >= segFrom).length;
    const prev = runs[runs.length - 1];
    if (prev && prev.count === count) prev.to = segTo;
    else runs.push({ from: segFrom, to: segTo, count });
  }
  return runs;
}

export interface EciCareerSource {
  url: string;
  kind: "official" | "court" | "press";
  host: string;
}

export interface EciCareerItem {
  post: string;
  from: string | null;
  to: string | null;
  /** The rendered date label — see the rules in `careerTimeline`'s doc comment. Never "present". */
  label: string;
  sources: EciCareerSource[];
  atCommission: boolean;
}

export interface EciCareerTimeline {
  dated: EciCareerItem[];
  undated: EciCareerItem[];
}

/** A source URL's trust kind (PHASE4-SPEC.md §2.4, `sourceKind(url)`): official (`gov.in`/`nic.in`), court
 *  (`indiankanoon.org`, `scobserver.in`, `sci.gov.in`) or press (anything else). */
export function sourceKind(url: string): { kind: "official" | "court" | "press"; label: string; host: string } {
  let host = url;
  try {
    host = new URL(url).host.replace(/^www\./, "");
  } catch {
    // leave host as the raw string — an unparsable URL still needs a label
  }
  if (host.endsWith("gov.in") || host.endsWith("nic.in")) return { kind: "official", label: "Official record", host };
  if (host === "indiankanoon.org" || host === "scobserver.in" || host === "sci.gov.in") return { kind: "court", label: "Court record", host };
  return { kind: "press", label: "Press report", host };
}

function careerDateLabel(from: string | null, to: string | null, ongoingOffice: boolean): string {
  if (from && to) return `${formatLooseDate(from)} – ${formatLooseDate(to)}`;
  if (!from && to) return `until ${formatLooseDate(to)}`;
  if (from && !to) return ongoingOffice ? `since ${formatLooseDate(from)}` : `from ${formatLooseDate(from)} · end date not in source`;
  return "—";
}

/** True when some still-open tenure (`to` null) names an office that `post` mentions — the rule that
 *  turns "from 2012 · end date not in source" into "since Feb 2025" for the one posting that is, in fact,
 *  the current office (PHASE4-SPEC.md §2.4). */
function postMatchesOpenTenure(post: string, tenure: EciTenure[] | undefined | null): boolean {
  const lower = post.toLowerCase();
  return (tenure ?? []).some((t) => t.office && t.to == null && lower.includes(String(t.office).toLowerCase()));
}

/** `details.career` (source order preserved) split into dated (oldest first) and undated items, each
 *  carrying its rendered label and its sources in `source_url`, `additional_source_url` order
 *  (PHASE4-SPEC.md §2.4). Replaces the deleted `detailLines()`/`careerLines()` pairing for this page:
 *  `career` gets its own structured render instead of a generic scalar dump. */
export function careerTimeline(details: Record<string, unknown>, tenure: EciTenure[] | undefined | null): EciCareerTimeline {
  const raw = Array.isArray(details.career) ? details.career : [];
  const items: EciCareerItem[] = raw
    .filter((c): c is Record<string, unknown> => typeof c === "object" && c !== null && typeof (c as Record<string, unknown>).post === "string")
    .map((c) => {
      const post = c.post as string;
      const from = typeof c.from === "string" ? c.from : null;
      const to = typeof c.to === "string" ? c.to : null;
      const sources: EciCareerSource[] = [];
      for (const key of ["source_url", "additional_source_url"]) {
        const url = c[key];
        if (typeof url === "string" && url) {
          const sk = sourceKind(url);
          sources.push({ url, kind: sk.kind, host: sk.host });
        }
      }
      return {
        post,
        from,
        to,
        label: careerDateLabel(from, to, postMatchesOpenTenure(post, tenure)),
        sources,
        atCommission: ECI_AT_COMMISSION_RE.test(post),
      };
    });
  const dated = items
    .filter((i) => i.from || i.to)
    .sort((a, b) => {
      const ak = a.from ?? a.to ?? "";
      const bk = b.from ?? b.to ?? "";
      return ak < bk ? -1 : ak > bk ? 1 : 0;
    });
  const undated = items.filter((i) => !i.from && !i.to);
  return { dated, undated };
}

/** "A. Sreenivas" -> "AS", "Rathan U. Kelkar" -> "RK", "Justice Sanjay Kumar" -> "SK" (PHASE4-SPEC.md
 *  §"PersonAvatar"). A leading "Justice" is dropped first; a lone middle initial (a length-1 token that
 *  isn't the first or last word) is dropped next; the initials are the first letter of what's left at
 *  each end. */
export function initials(name: string): string {
  const withoutTitle = name.replace(/^Justice\s+/i, "").trim();
  const raw = withoutTitle.split(/\s+/).filter(Boolean).map((t) => t.replace(/\.+$/, ""));
  const tokens = raw.filter((t, i) => i === 0 || i === raw.length - 1 || t.length > 1);
  if (tokens.length === 0) return "";
  const first = tokens[0];
  const last = tokens[tokens.length - 1];
  return `${(first[0] ?? "").toUpperCase()}${(last[0] ?? "").toUpperCase()}`;
}

export interface EciGroupMeta {
  /** The `<h2>` for this group's section on `/eci-files/people`. */
  heading: string;
  /** The short chip label used on cards and the profile header. */
  chip: string;
  description: string;
}

/** Group -> the copy in PHASE4-SPEC.md §1.1's table and §2.1's chip row. */
export const ECI_PERSON_GROUP_META: Record<EciPersonGroup, EciGroupMeta> = {
  commission: {
    heading: "The Commission",
    chip: "The Commission",
    description: "Chief Election Commissioners and Election Commissioners who served between 2019 and today.",
  },
  secretariat: {
    heading: "Senior officials at the Commission",
    chip: "Senior official",
    description: "Deputy and senior deputy election commissioners, the Director General (IT), the Commission's secretaries and its observers.",
  },
  state: {
    heading: "State Chief Electoral Officers",
    chip: "State election officer",
    description: "The officers who run the rolls and elections in each state, where the record names them.",
  },
  named: {
    heading: "Also named in the record",
    chip: "Named in the record",
    description: "Judges, lawyers, ministers and party leaders who appear in entries. They have no profile here. Each page lists the entries that name them.",
  },
};

export function personGroupMeta(group: EciPersonGroup): EciGroupMeta {
  return ECI_PERSON_GROUP_META[group];
}

/** The short photo credit for the caption under an avatar (PHASE4-SPEC.md §4.3): "PIB / ECI" when the
 *  original publisher was PIB, else "ECI". The full `attribution` string still goes in the link's `title`. */
export function photoCredit(photo: Pick<EciPhoto, "original_publisher">): string {
  return photo.original_publisher?.startsWith("Press Information Bureau") ? "PIB / ECI" : "ECI";
}

function monthsBetween(fromIso: string, toIso: string): number {
  const a = new Date(`${fromIso}T00:00:00Z`);
  const b = new Date(`${toIso}T00:00:00Z`);
  let months = (b.getUTCFullYear() - a.getUTCFullYear()) * 12 + (b.getUTCMonth() - a.getUTCMonth());
  if (b.getUTCDate() < a.getUTCDate()) months -= 1;
  return Math.max(0, months);
}

function formatDurationMonths(totalMonths: number): string {
  const yr = Math.floor(totalMonths / 12);
  const mo = totalMonths % 12;
  const parts: string[] = [];
  if (yr > 0) parts.push(`${yr} yr`);
  if (mo > 0 || parts.length === 0) parts.push(`${mo} mo`);
  return parts.join(" ");
}

export interface EciTenureDuration {
  total: string;
  byOffice: { office: string; label: string }[];
}

/** KeyFacts' "Time at the Commission" tile (PHASE4-SPEC.md §2.3): the sum of tenure spans with `from` set,
 *  up to `axis.to` (today), as "6 yr 6 mo", plus the same broken down per office for the context line. */
export function tenureDuration(
  tenure: EciTenure[] | undefined | null,
  axis: { from: string; to: string } = ECI_TENURE_AXIS,
): EciTenureDuration {
  const byOffice = new Map<string, number>();
  let totalMonths = 0;
  for (const t of tenure ?? []) {
    if (!t.from) continue;
    const to = t.to ?? axis.to;
    if (to < t.from) continue;
    const m = monthsBetween(t.from, to);
    totalMonths += m;
    const office = t.office ?? "—";
    byOffice.set(office, (byOffice.get(office) ?? 0) + m);
  }
  return {
    total: formatDurationMonths(totalMonths),
    byOffice: Array.from(byOffice.entries()).map(([office, m]) => ({ office, label: formatDurationMonths(m) })),
  };
}

/** The latest tenure segment on record (last one carrying a date) — "Office"/"In office" for the
 *  secretariat/state KeyFacts group and `StateOfficerRow`'s "In office" column. */
export function latestTenure(tenure: EciTenure[] | undefined | null): EciTenure | null {
  const dated = (tenure ?? []).filter((t) => t.from || t.to);
  return dated.length > 0 ? dated[dated.length - 1] : null;
}

/** One tenure -> "Mar 2025 – May 2026" / "since Jun 2025" / "—". Distinct from `formatTenure` (which joins
 *  every office into one "office, span" line per office and uses "present" for an open end) because
 *  `StateOfficerRow` and secretariat/state `KeyFacts` want exactly one span in this house style. */
export function formatTenureSpan(t: EciTenure | null | undefined): string {
  if (!t || !t.from) return "—";
  return t.to ? `${formatLooseDate(t.from)} – ${formatLooseDate(t.to)}` : `since ${formatLooseDate(t.from)}`;
}

/** The regime whose window contains `date` — used for the "Selected under" KeyFacts fallback when a
 *  commissioner has no row in `selections` (appointed under the executive convention, before 2019). */
export function regimeForDate(date: string | null | undefined, regimes: EciSelectionRegime[]): EciSelectionRegime | null {
  if (!date) return null;
  return regimes.find((r) => (!r.from_date || date >= r.from_date) && (!r.to_date || date < r.to_date)) ?? null;
}

const ECI_STATUS_ORDER: EciEntryStatus[] = ["documented", "reported", "claim", "response"];
const ECI_STATUS_PLURAL: Record<EciEntryStatus, string> = {
  documented: "documented", reported: "reported", claim: "claims", response: "responses",
};

const REGIME_SHORT: Record<string, string> = {
  convention: "Executive convention",
  baranwal: "Court's interim committee",
  act_2023: "2023 Act committee",
};

/** The regime key's short form used on both `KeyFacts`' "Selected under" tile and `SelectedByBlock`'s
 *  regime chip (PHASE4-SPEC.md §2.3, §2.5.1) — distinct from the fuller `EciSelectionRegime.label`. */
export function regimeShortLabel(key: string): string {
  return REGIME_SHORT[key] ?? key;
}

/** "Election Commissioner" -> "EC", "Chief Election Commissioner" -> "CEC" — the per-office context line
 *  on the commission `KeyFacts` "Time at the Commission" tile ("EC 11 mo · CEC 7 mo…"). */
export function officeAbbrev(office: string): string {
  if (/^Chief Election Commissioner$/.test(office)) return "CEC";
  if (/^Election Commissioner$/.test(office)) return "EC";
  return office;
}

/** "70 entries · 11 documented · 24 reported · 23 claims · 12 responses" — the text a `StatusCountBar`
 *  only ever echoes (PHASE4-SPEC.md §1.3: "The text is what carries the information; the bar only echoes
 *  it."). A status with a zero count is left out entirely. */
export function formatStatusCounts(total: number, counts: { documented: number; reported: number; claim: number; response: number }): string {
  const parts = [`${total} entr${total === 1 ? "y" : "ies"}`];
  for (const s of ECI_STATUS_ORDER) {
    if (counts[s] > 0) parts.push(`${counts[s]} ${ECI_STATUS_PLURAL[s]}`);
  }
  return parts.join(" · ");
}
// --- end phase 4 ---

// --- ECI Files phase 5 (views) ---
// Helpers for /eci-files/objections, /answers, /rules(+diff) and /courts(+case). `initials()` comes from phase 4's block above.

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
