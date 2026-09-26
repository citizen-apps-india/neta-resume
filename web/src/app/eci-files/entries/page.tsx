import type { Metadata } from "next";
import { Suspense } from "react";
import { SiteHeader } from "@/components/SiteHeader";
import { SectionHero } from "@/components/parliament/SectionHero";
import { EciEntriesSkeleton } from "@/components/skeletons";
import { EntriesFilterBar } from "@/components/eci-files/front/EntriesFilterBar";
import { EntriesYearNav, EARLIER_YEAR, type EciYearCount } from "@/components/eci-files/front/EntriesYearNav";
import { EntriesMonthSection } from "@/components/eci-files/front/EntriesMonthSection";
import { buildEntryMonths, keepReadingLabel, splitKeepReading, yearOf } from "@/components/eci-files/front/entriesGrouping";
import { DrawerFromParam } from "@/components/eci-files/views/DrawerFromParam";
import { getEciTimelineCompact, type EciCompactTimeline } from "@/lib/api";
import { ECI_LOAD_FAILED_MESSAGE } from "@/lib/eci-files";

export const metadata: Metadata = {
  title: "Every entry · ECI Files",
  description: "The complete sourced ECI Files record, year by year.",
};

// The record's fixed span (BRIEF.md: "1 January 2019 to today") — the year nav's bounds.
const RECORD_START_YEAR = 2019;

type Params = {
  year?: string; lane?: string; status?: string; topic?: string; person?: string; q?: string; checked?: string; entry?: string;
};

/** The filters, year nav and grouped rows. Its own async component so the static `SectionHero` paints
 *  immediately and this streams in beneath it. Fetches the whole record once (subject to the current
 *  lane/status/topic/person filters, but not the year) so the year nav's counts and the selected year's
 *  rows come from a single request — `q` and "checked only" then filter that in memory, since the API
 *  has no full-text search of its own. */
async function EntriesBody({ year, currentYear, lane, status, topic, person, q, checkedOnly, entryId }: {
  year: number | typeof EARLIER_YEAR;
  currentYear: number;
  lane?: string;
  status?: string;
  topic?: string;
  person?: string;
  q?: string;
  checkedOnly: boolean;
  entryId?: string;
}) {
  let timeline: EciCompactTimeline | null = null;
  try {
    timeline = await getEciTimelineCompact({ lane, status, topic, person });
  } catch {
    timeline = null;
  }

  if (!timeline) {
    return <p style={{ color: "var(--muted)", padding: "24px 4px" }}>{ECI_LOAD_FAILED_MESSAGE}</p>;
  }

  const yearCounts = new Map<number, number>();
  let earlierCount = 0;
  for (const e of timeline.entries) {
    const y = yearOf(e.date);
    if (y === null) continue;
    if (y < RECORD_START_YEAR) earlierCount += 1;
    else yearCounts.set(y, (yearCounts.get(y) ?? 0) + 1);
  }
  const years: EciYearCount[] = [];
  // N8: entries dated before the record's fixed start year had no tab to reach them — fold them into
  // one "Earlier" stop instead of a tab per pre-2019 year, most of which would show a count of one.
  if (earlierCount > 0) years.push({ year: EARLIER_YEAR, count: earlierCount });
  for (let y = RECORD_START_YEAR; y <= currentYear; y++) years.push({ year: y, count: yearCounts.get(y) ?? 0 });

  const qLower = q?.toLowerCase();
  const filtered = timeline.entries.filter((e) => {
    const y = yearOf(e.date);
    if (year === EARLIER_YEAR ? y === null || y >= RECORD_START_YEAR : y !== year) return false;
    if (checkedOnly && e.check_status !== "checked") return false;
    if (qLower && !(e.title.toLowerCase().includes(qLower) || e.people.some((p) => p.name.toLowerCase().includes(qLower)))) return false;
    return true;
  });
  const unchecked = filtered.filter((e) => e.check_status === "unchecked").length;

  const months = buildEntryMonths(filtered);
  const { visible, hidden } = splitKeepReading(months);

  const preserve = {
    year: String(year), lane, status, topic, person, q, checked: checkedOnly ? "1" : undefined,
  };
  const yearLabel = year === EARLIER_YEAR ? `before ${RECORD_START_YEAR}` : year;

  return (
    <>
      <EntriesFilterBar
        lanes={timeline.lanes} topics={timeline.topics} people={timeline.people}
        lane={lane} status={status} topic={topic} person={person} q={q} checked={checkedOnly}
      />
      <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 8 }}>
        <EntriesYearNav years={years} activeYear={year} preserve={{ lane, status, topic, person, q, checked: checkedOnly ? "1" : undefined }} />
        <span className="mono" style={{ fontSize: 12.5, color: "var(--muted)" }}>
          {filtered.length} entr{filtered.length === 1 ? "y" : "ies"} {year === EARLIER_YEAR ? yearLabel : `in ${yearLabel}`}
          {unchecked > 0 && <> · {unchecked} not yet checked</>}
        </span>
      </div>

      {filtered.length === 0 ? (
        <p style={{ color: "var(--muted)", padding: "24px 4px" }}>No entries match these filters.</p>
      ) : (
        <div style={{ maxWidth: 920 }}>
          {visible.map((m) => <EntriesMonthSection key={m.key} month={m} preserve={preserve} />)}
          {hidden.length > 0 && (
            <details className="eci-keep-reading">
              <summary>{keepReadingLabel(hidden, yearLabel)}</summary>
              <div>{hidden.map((m) => <EntriesMonthSection key={m.key} month={m} preserve={preserve} />)}</div>
            </details>
          )}
        </div>
      )}

      {entryId && (
        <Suspense fallback={null}>
          <DrawerFromParam id={entryId} basePath="/eci-files/entries" preserve={preserve} />
        </Suspense>
      )}
    </>
  );
}

export default async function EciEntriesPage({ searchParams }: { searchParams: Promise<Params> }) {
  const sp = await searchParams;
  const lane = sp.lane || undefined;
  const status = sp.status || undefined;
  const topic = sp.topic || undefined;
  const person = sp.person || undefined;
  const q = sp.q?.trim() || undefined;
  const checkedOnly = sp.checked === "1";
  const entryId = sp.entry || undefined;

  const currentYear = new Date().getUTCFullYear();
  const requested = Number(sp.year);
  const year: number | typeof EARLIER_YEAR =
    sp.year === EARLIER_YEAR
      ? EARLIER_YEAR
      : Number.isInteger(requested) && requested >= RECORD_START_YEAR && requested <= currentYear
        ? requested
        : currentYear;

  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 980, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
        <SectionHero
          eyebrow="ECI Files · Full record"
          title="Every entry"
          subtitle="The complete sourced record, one year at a time. Jump to a year or filter by lane."
          backHref="/eci-files"
          backLabel="ECI Files"
        />
        <Suspense fallback={<EciEntriesSkeleton />}>
          <EntriesBody
            year={year} currentYear={currentYear} lane={lane} status={status} topic={topic} person={person}
            q={q} checkedOnly={checkedOnly} entryId={entryId}
          />
        </Suspense>
      </main>
    </>
  );
}
