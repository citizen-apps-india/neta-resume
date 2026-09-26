// Pure grouping/folding helpers for /eci-files/entries — kept JSX-free and dependency-free (just
// EciCompactEntry) so they're usable from a server component without pulling React into a lib file.
// Not a hotspot: nothing else imports this yet, so it's a plain new file rather than an appended block.

import type { EciCompactEntry } from "@/types/eci-files";

const MONTH_FULL = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];
const MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** The calendar year of an entry's date, in UTC — null when there's no usable date. */
export function yearOf(date: string | null): number | null {
  if (!date) return null;
  const y = Number(date.slice(0, 4));
  return Number.isFinite(y) ? y : null;
}

/** "1 Jan" for a day-precision date; the plain year/month label otherwise (a year- or month-precision
 *  entry has no day worth printing in the date rail). */
export function entryDayLabel(entry: Pick<EciCompactEntry, "date" | "date_precision">): string {
  if (!entry.date) return "—";
  if (entry.date_precision !== "day") {
    const d = new Date(`${entry.date}T00:00:00Z`);
    if (isNaN(d.getTime())) return "—";
    return entry.date_precision === "year" ? String(d.getUTCFullYear()) : `${MONTH_ABBR[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
  }
  const d = new Date(`${entry.date}T00:00:00Z`);
  if (isNaN(d.getTime())) return "—";
  return `${d.getUTCDate()} ${MONTH_ABBR[d.getUTCMonth()]}`;
}

/** One row unit in a month's list: a single entry, or 2+ entries on the same day in the same lane —
 *  the "same-day and duplicate folding" the design calls for, without inventing a collective headline. */
export type EciEntryRowUnit = EciCompactEntry | EciCompactEntry[];

export interface EciMonthBucket {
  /** Sort/React key. */
  key: string;
  /** "January 2026", or null for a year-precision entry (no month on record — rendered without a heading). */
  label: string | null;
  rows: EciEntryRowUnit[];
  count: number;
}

/** Folds consecutive entries that share both a date and a lane — the two cases the design shows (one
 *  story carried by more than one record; several same-lane entries landing on the same day) — while
 *  never merging entries from different lanes just because the date matches. */
function foldSameDay(entries: EciCompactEntry[]): EciEntryRowUnit[] {
  const out: EciEntryRowUnit[] = [];
  for (const e of entries) {
    const last = out[out.length - 1];
    if (Array.isArray(last)) {
      if (last[0].date === e.date && last[0].lane === e.lane) {
        last.push(e);
        continue;
      }
    } else if (last && last.date === e.date && last.lane === e.lane) {
      out[out.length - 1] = [last, e];
      continue;
    }
    out.push(e);
  }
  return out;
}

/** Groups already date-ascending entries into month buckets (full "Month Year" label; year-precision
 *  entries land in their own unlabelled bucket, same convention as `groupEciTimeline`), folding same-day
 *  duplicates within each bucket. */
export function buildEntryMonths(entries: EciCompactEntry[]): EciMonthBucket[] {
  const buckets: { key: string; label: string | null; entries: EciCompactEntry[] }[] = [];
  for (const e of entries) {
    let key = "undated";
    let label: string | null = null;
    if (e.date) {
      const d = new Date(`${e.date}T00:00:00Z`);
      if (!isNaN(d.getTime())) {
        if (e.date_precision === "year") {
          key = `${d.getUTCFullYear()}-none`;
        } else {
          key = `${d.getUTCFullYear()}-${d.getUTCMonth()}`;
          label = `${MONTH_FULL[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
        }
      }
    }
    const cur = buckets[buckets.length - 1];
    if (!cur || cur.key !== key) buckets.push({ key, label, entries: [e] });
    else cur.entries.push(e);
  }
  return buckets.map((b) => ({ key: b.key, label: b.label, rows: foldSameDay(b.entries), count: b.entries.length }));
}

/** Splits month buckets into what's shown up front and what's folded behind "keep reading" — the whole
 *  first month always shows, then buckets keep accumulating until the visible row count clears
 *  `threshold`, so a sparse year isn't cut after two tiny months and a busy one still gets capped. */
export function splitKeepReading(months: EciMonthBucket[], threshold = 24): { visible: EciMonthBucket[]; hidden: EciMonthBucket[] } {
  let acc = 0;
  let cut = months.length;
  for (let i = 0; i < months.length; i++) {
    if (i > 0 && acc >= threshold) {
      cut = i;
      break;
    }
    acc += months[i].count;
  }
  return { visible: months.slice(0, cut), hidden: months.slice(cut) };
}

/** "Keep reading: March – September 2026 · 113 entries" — the folded months' span and total. */
export function keepReadingLabel(hidden: EciMonthBucket[], year: number | string): string {
  const total = hidden.reduce((a, b) => a + b.count, 0);
  const first = hidden[0]?.label?.split(" ")[0] ?? "Undated";
  const last = hidden[hidden.length - 1]?.label?.split(" ")[0] ?? "Undated";
  const span = first === last ? first : `${first} – ${last}`;
  return `Keep reading: ${span} ${year} · ${total} ${total === 1 ? "entry" : "entries"}`;
}
