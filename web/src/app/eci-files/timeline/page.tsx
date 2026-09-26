import type { Metadata } from "next";
import { Suspense } from "react";
import { SiteHeader } from "@/components/SiteHeader";
import { SectionHero } from "@/components/parliament/SectionHero";
import { EciTimelineSkeleton } from "@/components/skeletons";
import { TimelineView } from "@/components/eci-files/timeline/TimelineView";
import { getEciDensity, getEciSummary, getEciTimelineCompactByState } from "@/lib/api";
import { defaultEciWindow, densityByMonth, ECI_LANE_ORDER } from "@/lib/eci-files";
import type { EciFilesLane } from "@/types/eci-files";

export const metadata: Metadata = {
  title: "Timeline · ECI Files",
  description: "Every sourced ECI Files entry, by date — search it, filter by lane, and open any entry in place.",
  robots: { index: false, follow: false },
};

const BASE_PATH = "/eci-files/timeline";

type Params = {
  topic?: string; person?: string; lane?: string; checked?: string; q?: string; from?: string; to?: string; entry?: string;
};

/** Fetches the first paint — the whole-record density (for the heat map/month strip), the key moments,
 *  and the compact timeline for the requested (or default) window — then hands off to `TimelineView`,
 *  which owns every filter/window/entry change client-side from here on. Its own async component so the
 *  hero paints immediately (matches the previous `TimelineBody` streaming shape). */
async function TimelineBody({ topic, person, lane, checked, q, from, to, entry }: Params) {
  const range = { from: from ?? defaultEciWindow().from, to: to ?? defaultEciWindow().to };

  let density = null, timeline = null, summary = null;
  try {
    [density, timeline, summary] = await Promise.all([
      getEciDensity(),
      getEciTimelineCompactByState({ topic, person, from: range.from, to: range.to }),
      getEciSummary(),
    ]);
  } catch {
    density = null;
    timeline = null;
    summary = null;
  }

  if (!density || !timeline || !summary) {
    return (
      <p style={{ color: "var(--muted)", padding: "24px 4px" }}>
        The record hasn&apos;t loaded — try again in a moment.
      </p>
    );
  }

  const initialLanes = lane
    ? (lane.split(",").filter((l): l is EciFilesLane => (ECI_LANE_ORDER as string[]).includes(l)))
    : undefined;

  return (
    <TimelineView
      basePath={BASE_PATH}
      initialWindow={range}
      initialTopic={topic}
      initialPerson={person}
      initialLanes={initialLanes}
      initialChecked={checked === "1"}
      initialQuery={q}
      initialEntry={entry}
      initialTimeline={timeline}
      months={densityByMonth(density.months)}
      keyMoments={summary.key_moments}
      recordTotal={summary.counts.dated_entries ?? summary.counts.entries}
    />
  );
}

export default async function EciTimelinePage({ searchParams }: { searchParams: Promise<Params> }) {
  const sp = await searchParams;

  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 1180, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
        <SectionHero
          eyebrow="ECI FILES · TIMELINE"
          title="What happened, in order"
          subtitle="Every sourced entry, by date. Search it, filter by lane, and open any entry in place."
          backHref="/eci-files"
          backLabel="ECI Files"
        />
        <Suspense fallback={<EciTimelineSkeleton />}>
          <TimelineBody {...sp} />
        </Suspense>
      </main>
    </>
  );
}
