// Display helpers specific to ECI Files: date precision, status-chip tokens, and year/month grouping
// for the timeline. Kept separate from lib/format.ts because this vocabulary (documented/reported/
// claim/response, day/month/year precision) belongs to this one source.

import type { EciEntry, EciEntryStatus } from "@/types/eci-files";

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
  fg: string;
  bg: string;
  bd: string;
}

/** Status -> chip tokens. Each status reads as a distinct colour, never a verdict — "documented" is a
 *  provenance fact (we opened a primary document), not a claim that the underlying event is true. */
export const ECI_STATUS_META: Record<EciEntryStatus, EciStatusMeta> = {
  documented: { label: "Document", fg: "var(--accent-soft-fg)", bg: "var(--accent-soft)", bd: "var(--accent-soft-bd)" },
  reported: { label: "Reported", fg: "var(--sev3)", bg: "var(--sev3-bg)", bd: "var(--border2)" },
  claim: { label: "Claim", fg: "var(--sev2)", bg: "var(--sev2-bg)", bd: "var(--sev2-bd)" },
  response: { label: "Response", fg: "var(--ok)", bg: "var(--ok-bg)", bd: "var(--ok)" },
};

export function eciStatusMeta(status: EciEntryStatus): EciStatusMeta {
  return ECI_STATUS_META[status] ?? { label: status, fg: "var(--muted)", bg: "var(--sunken)", bd: "var(--border2)" };
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
    .filter(([, v]) => v !== null && v !== undefined && (typeof v === "string" || typeof v === "number" || typeof v === "boolean"))
    .map(([k, v]) => ({ label: humanizeKey(k), value: String(v) }));
}
