import type { Metadata } from "next";
import { Suspense } from "react";
import { SiteHeader } from "@/components/SiteHeader";
import { SectionHero } from "@/components/parliament/SectionHero";
import { EciFrontSkeleton } from "@/components/skeletons";
import { FrontHeroPanel } from "@/components/eci-files/front/FrontHeroPanel";
import { FrontSectionTiles, type FrontTile } from "@/components/eci-files/front/FrontSectionTiles";
import {
  TimelineIcon, StatesIcon, PeopleIcon, ObjectionsIcon, AnswersIcon, RulesIcon, CourtsIcon,
} from "@/components/eci-files/front/FrontIcons";
import { FrontKeyMoments } from "@/components/eci-files/front/FrontKeyMoments";
import { FrontAbout } from "@/components/eci-files/front/FrontAbout";
import {
  getEciSummary, getEciDensity, getEciStates, getEciPeople, getEciObjections, getEciAnswers, getEciRules, getEciCourts,
  type EciSummary, type EciDensity,
} from "@/lib/api";
import { densityByMonth, ECI_LOAD_FAILED_MESSAGE } from "@/lib/eci-files";

// Hidden until the owner approves: noindex/nofollow, unlinked, kept out of sitemap.ts. See
// docs/eci-files/SPEC.md — "Launch is gated."
export const metadata: Metadata = {
  title: "ECI Files",
  description: "A sourced, dated record of the Election Commission of India, 2019 to today.",
  robots: { index: false, follow: false },
};

/** Awaits one of the tile fetchers and reduces it to the single count its tile shows — `null` on any
 *  failure, so one flaky endpoint dims its own tile ("—") instead of blanking the whole page. */
async function safeCount<T>(promise: Promise<T>, pick: (v: T) => number): Promise<number | null> {
  try {
    return pick(await promise);
  } catch {
    return null;
  }
}

/** The summary and density payloads drive the hero, the key moments and the footer counts; the tile
 *  counts are fetched alongside, independently. Its own async component so the static `SectionHero`
 *  paints immediately and this streams in beneath it — same pattern as the India Dashboard (`IndiaBody`). */
async function EciFrontBody() {
  let summary: EciSummary | null = null;
  let density: EciDensity | null = null;
  try {
    [summary, density] = await Promise.all([getEciSummary(), getEciDensity()]);
  } catch {
    summary = null;
    density = null;
  }

  if (!summary || !density) {
    return <p style={{ color: "var(--muted)", padding: "24px 4px" }}>{ECI_LOAD_FAILED_MESSAGE}</p>;
  }

  const [statesCount, peopleCount, objectionsCount, answersCount, rulesCount, courtsCount] = await Promise.all([
    safeCount(getEciStates(), (s) => s.regions.filter((r) => r.has_figures).length),
    safeCount(getEciPeople(), (p) => p.length),
    safeCount(getEciObjections(), (o) => o.reported_total),
    safeCount(getEciAnswers(), (a) => a.counts.rows),
    safeCount(getEciRules(), (r) => r.counts.rules),
    safeCount(getEciCourts(), (c) => c.cases.length),
  ]);

  // Colour follows the lane a section reads closest to (Objections -> Inside the Commission, Answers ->
  // Claims, Courts -> Courts); Timeline/Rules use the section accent and the document trust colour.
  const tiles: FrontTile[] = [
    { href: "/eci-files/timeline", count: summary.counts.entries, unit: "entries", title: "The whole record, in order", color: "var(--eci-ink)", icon: <TimelineIcon /> },
    { href: "/eci-files/numbers", count: statesCount, unit: "states & UTs with figures", title: "The rolls, state by state", color: "var(--eci-doc)", icon: <StatesIcon /> },
    { href: "/eci-files/people", count: peopleCount, unit: "people", title: "Commissioners and officials", color: "var(--muted)", icon: <PeopleIcon /> },
    { href: "/eci-files/objections", count: objectionsCount, unit: "objections", title: "Raised inside the Commission", color: "var(--eci-lane-inside)", icon: <ObjectionsIcon /> },
    { href: "/eci-files/answers", count: answersCount, unit: "charges", title: "Claims and their answers", color: "var(--eci-lane-claims)", icon: <AnswersIcon /> },
    { href: "/eci-files/rules", count: rulesCount, unit: "rules", title: "What changed, and when", color: "var(--eci-doc)", icon: <RulesIcon /> },
    { href: "/eci-files/courts", count: courtsCount, unit: "cases", title: "Orders and case law", color: "var(--eci-lane-courts)", icon: <CourtsIcon /> },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 32 }}>
      <FrontHeroPanel headline={summary.headline} months={densityByMonth(density.months)} />
      <FrontSectionTiles tiles={tiles} />
      <FrontKeyMoments moments={summary.key_moments} />
      <FrontAbout counts={summary.counts} lastLoaded={summary.last_loaded} />
    </div>
  );
}

export default function EciFilesPage() {
  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 1100, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
        <SectionHero
          eyebrow="ECI Files · Sourced record"
          title="What happened at the Election Commission"
          subtitle="The sourced record, 2019 to today. Start with the numbers, the timeline, or the people."
        />
        <Suspense fallback={<EciFrontSkeleton />}>
          <EciFrontBody />
        </Suspense>
      </main>
    </>
  );
}
