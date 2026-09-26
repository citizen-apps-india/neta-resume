import type { Metadata } from "next";
import { Suspense } from "react";
import { notFound } from "next/navigation";
import { SiteHeader } from "@/components/SiteHeader";
import { SectionHero } from "@/components/parliament/SectionHero";
import { StatePicker } from "@/components/eci-files/numbers/StatePicker";
import { StateMetricTiles } from "@/components/eci-files/numbers/StateMetricTiles";
import { StageChart } from "@/components/eci-files/numbers/StageChart";
import { AfterFinalFigures } from "@/components/eci-files/numbers/AfterFinalFigures";
import { DraftCaveat } from "@/components/eci-files/numbers/DraftCaveat";
import { StateNotes } from "@/components/eci-files/numbers/StateNotes";
import { StateEventRows } from "@/components/eci-files/numbers/StateEventRows";
import { EntryDrawer } from "@/components/eci-files/EntryDrawer";
import { EntryDetail } from "@/components/eci-files/EntryDetail";
import { getEciState, getEciStates, getEciEntry, getEciTimelineCompactByState } from "@/lib/api";
import { isEciRegionSlug, romanPhase } from "@/lib/eci-numbers";
import { formatLooseDate, loadEciItem, ECI_LOAD_FAILED_MESSAGE } from "@/lib/eci-files";
import type { EciRegionSummary } from "@/types/eci-files";

type RouteParams = { state: string };
type Search = { entry?: string };

export async function generateMetadata({ params }: { params: Promise<RouteParams> }): Promise<Metadata> {
  const { state } = await params;
  if (!isEciRegionSlug(state)) {
    return { title: "State not found · The numbers · ECI Files", robots: { index: false, follow: false } };
  }
  const page = await getEciState(state).catch(() => null);
  const name = page?.region.name ?? "State not found";
  return {
    title: `${name} · The numbers · ECI Files`,
    description: `SIR figures for ${name}, taken from the cited entries in the record.`,
    robots: { index: false, follow: false },
  };
}

function subtitleFor(region: EciRegionSummary): string {
  if (region.exercise === "special_revision") {
    return "Special Revision — a different exercise from the Special Intensive Revision run in other States. Its figures are shown here but kept out of the SIR comparisons.";
  }
  if (!region.has_figures) {
    const base = `No SIR figures for ${region.name} are in the record yet.`;
    return region.phase ? `${base} It is in Phase ${romanPhase(region.phase)} of the SIR.` : base;
  }
  const dated = region.stages.map((s) => s.as_of).filter((d): d is string => Boolean(d)).sort();
  const first = dated[0] ? formatLooseDate(dated[0]) : null;
  const last = dated[dated.length - 1] ? formatLooseDate(dated[dated.length - 1]) : null;
  const span = first && last ? (first === last ? ` as of ${first}` : ` from ${first} to ${last}`) : "";
  const figureCount = region.stages.length === 1 ? "1 figure" : `${region.stages.length} figures`;
  return `Special Intensive Revision, Phase ${romanPhase(region.phase)}. ${figureCount} on record${span}.`;
}

async function EntryDrawerBody({ id, basePath }: { id: string; basePath: string }) {
  const full = await getEciEntry(id).catch(() => null);
  if (!full) return null;
  return (
    <EntryDrawer>
      <EntryDetail entry={full} basePath={basePath} />
    </EntryDrawer>
  );
}

export default async function EciNumbersStatePage({ params, searchParams }: { params: Promise<RouteParams>; searchParams: Promise<Search> }) {
  const { state } = await params;
  const { entry } = await searchParams;
  if (!isEciRegionSlug(state)) notFound();

  const [result, overview, timeline] = await Promise.all([
    loadEciItem(() => getEciState(state)),
    getEciStates().catch(() => null),
    getEciTimelineCompactByState({ state }).catch(() => null),
  ]);
  if (result.status === "not_found") notFound();
  if (result.status === "error") {
    return (
      <>
        <SiteHeader />
        <main style={{ maxWidth: 900, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
          <p style={{ color: "var(--muted)", padding: "24px 4px" }}>{ECI_LOAD_FAILED_MESSAGE}</p>
        </main>
      </>
    );
  }
  const page = result.data;

  const region = page.region;
  const basePath = `/eci-files/numbers/${state}`;
  const entries = timeline?.entries ?? [];

  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 900, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
        <SectionHero
          eyebrow="ECI FILES · THE NUMBERS"
          title={region.name}
          backHref="/eci-files/numbers"
          backLabel="The numbers"
          subtitle={subtitleFor(region)}
        />

        <div style={{ marginBottom: 24 }}>
          <StatePicker regions={overview?.regions ?? [{ slug: region.slug, name: region.name, has_figures: region.has_figures, exercise: region.exercise, stages: region.stages }]} current={state} compact />
        </div>

        <StateMetricTiles region={region} />
        <StageChart region={region} basePath={basePath} />
        <AfterFinalFigures region={region} basePath={basePath} />
        {region.has_figures && <DraftCaveat lastAsOf={overview?.last_as_of ?? null} />}
        <StateNotes region={region} notes={page.notes} basePath={basePath} />

        <section style={{ marginTop: 30 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap", gap: 10, marginBottom: 4 }}>
            <h2 className="serif" style={{ fontSize: 17, fontWeight: 600, margin: 0 }}>Events behind these numbers</h2>
          </div>
          <StateEventRows entries={entries} regionName={region.name} basePath={basePath} state={state} />
        </section>

        {entry && (
          <Suspense fallback={null}>
            <EntryDrawerBody id={entry} basePath={basePath} />
          </Suspense>
        )}
      </main>
    </>
  );
}
