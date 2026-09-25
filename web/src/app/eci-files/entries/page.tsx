import type { Metadata } from "next";
import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
import { SectionHero } from "@/components/parliament/SectionHero";
import { Filters } from "@/components/eci-files/Filters";
import { Timeline } from "@/components/eci-files/Timeline";
import { getEciTimeline, type EciTimeline } from "@/lib/api";

export const metadata: Metadata = {
  title: "Every entry · ECI Files",
  description: "The complete sourced ECI Files record, year by year.",
  robots: { index: false, follow: false },
};

// The record's fixed span (BRIEF.md: "1 January 2019 to today") — the year pager's bounds.
const RECORD_START_YEAR = 2019;

function yearHref(year: number, topic?: string, person?: string): string {
  const p = new URLSearchParams();
  p.set("year", String(year));
  if (topic) p.set("topic", topic);
  if (person) p.set("person", person);
  return `/eci-files/entries?${p.toString()}`;
}

function YearPager({ year, currentYear, topic, person }: { year: number; currentYear: number; topic?: string; person?: string }) {
  const prevDisabled = year <= RECORD_START_YEAR;
  const nextDisabled = year >= currentYear;
  const btn = (disabled: boolean): React.CSSProperties => ({
    fontFamily: "var(--font-serif)", fontSize: 13, fontWeight: 600, padding: "8px 16px", borderRadius: 9,
    border: "1px solid var(--border)", background: "var(--card2)", color: disabled ? "var(--faint)" : "var(--ink)",
    textDecoration: "none", pointerEvents: disabled ? "none" : "auto", opacity: disabled ? 0.5 : 1,
  });
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 16, margin: "8px 0 22px" }}>
      <Link href={yearHref(year - 1, topic, person)} className="btnGhost tap" style={btn(prevDisabled)} aria-disabled={prevDisabled}>
        ← {year - 1}
      </Link>
      <span className="mono serif" style={{ fontSize: 20, fontWeight: 600, color: "var(--ink)", minWidth: 64, textAlign: "center" }}>
        {year}
      </span>
      <Link href={yearHref(year + 1, topic, person)} className="btnGhost tap" style={btn(nextDisabled)} aria-disabled={nextDisabled}>
        {year + 1} →
      </Link>
    </div>
  );
}

export default async function EciEntriesPage({
  searchParams,
}: {
  searchParams: Promise<{ topic?: string; person?: string; year?: string }>;
}) {
  const sp = await searchParams;
  const topic = sp.topic || undefined;
  const person = sp.person || undefined;
  const currentYear = new Date().getUTCFullYear();
  const requested = Number(sp.year);
  const year = Number.isInteger(requested) && requested >= RECORD_START_YEAR && requested <= currentYear ? requested : currentYear;

  let timeline: EciTimeline | null = null;
  try {
    timeline = await getEciTimeline({ topic, person, from: `${year}-01-01`, to: `${year}-12-31` });
  } catch {
    timeline = null;
  }

  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 900, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
        <SectionHero
          eyebrow="ECI FILES · FULL RECORD"
          title="Every entry"
          subtitle="The complete sourced record, one year at a time — the deep dive behind the lane timeline, with every citation attached."
          backHref="/eci-files"
          backLabel="ECI Files"
        />

        {timeline === null ? (
          <p style={{ color: "var(--muted)", padding: "24px 4px" }}>
            The record hasn&apos;t loaded — try again in a moment.
          </p>
        ) : (
          <>
            <Filters
              basePath="/eci-files/entries"
              topics={timeline.topics}
              people={timeline.people}
              topic={topic}
              person={person}
              preserve={{ year: String(year) }}
            />
            <YearPager year={year} currentYear={currentYear} topic={topic} person={person} />
            <div className="mono" style={{ fontSize: 11.5, color: "var(--muted)", marginBottom: 16, textAlign: "center" }}>
              {timeline.entries.length} entr{timeline.entries.length === 1 ? "y" : "ies"} in {year}
              {" · "}
              {timeline.counts.unchecked} not yet checked
            </div>
            <Timeline entries={timeline.entries} />
          </>
        )}

        <div style={{ marginTop: 26, textAlign: "center" }}>
          <Link href="/eci-files/timeline" className="mono" style={{ fontSize: 12, color: "var(--accent-2)", textDecoration: "none" }}>
            ← Back to the lane timeline
          </Link>
        </div>
      </main>
    </>
  );
}
