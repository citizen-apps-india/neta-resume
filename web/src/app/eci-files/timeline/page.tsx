import type { Metadata } from "next";
import { Suspense } from "react";
import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
import { SectionHero } from "@/components/parliament/SectionHero";
import { EciTimelineSkeleton } from "@/components/skeletons";
import { DensityStrip } from "@/components/eci-files/DensityStrip";
import { Filters } from "@/components/eci-files/Filters";
import { StatusLegend } from "@/components/eci-files/StatusLegend";
import { LaneTimeline } from "@/components/eci-files/LaneTimeline";
import { EntryDrawer } from "@/components/eci-files/EntryDrawer";
import { EntryDetail } from "@/components/eci-files/EntryDetail";
import { getEciDensity, getEciEntry, getEciTimelineCompact, type EciCompactTimeline, type EciDensity } from "@/lib/api";
import { defaultEciWindow, densityByMonth } from "@/lib/eci-files";

export const metadata: Metadata = {
  title: "Lane timeline · ECI Files",
  description: "Five lanes — Commission, Inside the Commission, Courts, Claims, Responses — by date.",
  robots: { index: false, follow: false },
};

type Params = {
  lane?: string; topic?: string; person?: string; from?: string; to?: string; entry?: string;
};

/** The overview strip + lane dots for the current window. Its own async component so the hero paints
 *  immediately (REDESIGN-SPEC §"Loading": fetches `fields=compact` only — the first paint never pulls the
 *  whole record). */
async function TimelineBody({ lane, topic, person, from, to, entry }: Params) {
  const range = { from: from ?? defaultEciWindow().from, to: to ?? defaultEciWindow().to };

  let density: EciDensity | null = null;
  let timeline: EciCompactTimeline | null = null;
  try {
    [density, timeline] = await Promise.all([
      getEciDensity(),
      getEciTimelineCompact({ lane, topic, person, from: range.from, to: range.to }),
    ]);
  } catch {
    density = null;
    timeline = null;
  }

  if (!density || !timeline) {
    return (
      <p style={{ color: "var(--muted)", padding: "24px 4px" }}>
        The record hasn&apos;t loaded — try again in a moment.
      </p>
    );
  }

  const months = densityByMonth(density.months);

  return (
    <>
      <DensityStrip months={months} from={range.from} to={range.to} />

      <Filters
        basePath="/eci-files/timeline"
        lanes={timeline.lanes}
        topics={timeline.topics}
        people={timeline.people}
        lane={lane}
        topic={topic}
        person={person}
        preserve={{ from: range.from, to: range.to }}
      />

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10, marginBottom: 12 }}>
        <StatusLegend />
        <span className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>
          {timeline.entries.length} entr{timeline.entries.length === 1 ? "y" : "ies"} in this window
        </span>
      </div>

      <LaneTimeline entries={timeline.entries} from={range.from} to={range.to} activeId={entry} />

      {entry && (
        <Suspense fallback={null}>
          <EntryDrawerBody id={entry} preserve={{ lane, topic, person, from: range.from, to: range.to }} />
        </Suspense>
      )}
    </>
  );
}

/** Fetches the one full entry the drawer needs, on demand — never the whole record (REDESIGN-SPEC
 *  §"Loading"). A separate async component so it streams independently of the (already-visible) dots. */
async function EntryDrawerBody({ id, preserve }: { id: string; preserve: Record<string, string | undefined> }) {
  const full = await getEciEntry(id).catch(() => null);
  if (!full) return null;
  return (
    <EntryDrawer>
      <EntryDetail entry={full} preserve={preserve} />
    </EntryDrawer>
  );
}

export default async function EciTimelinePage({ searchParams }: { searchParams: Promise<Params> }) {
  const sp = await searchParams;

  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 1080, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
        <SectionHero
          eyebrow="ECI FILES · TIMELINE"
          title="The lane timeline"
          subtitle="Five lanes by date — Commission, Inside the Commission, Courts, Claims, Responses. Pick a window on the strip below, then open any dot for the full, sourced entry."
          backHref="/eci-files"
          backLabel="ECI Files"
        />
        <Suspense fallback={<EciTimelineSkeleton />}>
          <TimelineBody {...sp} />
        </Suspense>
        <div style={{ marginTop: 26 }}>
          <Link href="/eci-files/entries" className="mono" style={{ fontSize: 12, color: "var(--accent-2)", textDecoration: "none" }}>
            Browse every entry, year by year →
          </Link>
        </div>
      </main>
    </>
  );
}
