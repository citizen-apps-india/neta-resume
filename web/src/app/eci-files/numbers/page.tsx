import type { Metadata } from "next";
import { Suspense } from "react";
import Link from "next/link";
import { redirect } from "next/navigation";
import { SiteHeader } from "@/components/SiteHeader";
import { SectionHero } from "@/components/parliament/SectionHero";
import { EciNumbersSkeleton } from "@/components/skeletons";
import { StatePicker } from "@/components/eci-files/numbers/StatePicker";
import { NationalSummary, NationalPhaseBreakdown } from "@/components/eci-files/numbers/NationalSummary";
import { DraftCaveat } from "@/components/eci-files/numbers/DraftCaveat";
import { StateTileGrid } from "@/components/eci-files/numbers/StateTileGrid";
import { StateTileLegend } from "@/components/eci-files/numbers/StateTileLegend";
import { StateTable } from "@/components/eci-files/numbers/StateTable";
import { HowWeCounted } from "@/components/eci-files/numbers/HowWeCounted";
import { EntryDrawer } from "@/components/eci-files/EntryDrawer";
import { EntryDetail } from "@/components/eci-files/EntryDetail";
import { getEciStates, getEciEntry, type EciStatesOverview } from "@/lib/api";
import { ECI_METRICS, ECI_METRIC_FOOTNOTE, buildTileViewModels, eciMetricByParam, isEciRegionSlug } from "@/lib/eci-numbers";

// Gated: noindex/nofollow, unlinked from SiteHeader/homepage, out of sitemap.ts (PHASE3-SPEC.md §3.3).
export const metadata: Metadata = {
  title: "The numbers · ECI Files",
  description: "Special Intensive Revision (SIR) figures for every State and Union Territory, state by state.",
  robots: { index: false, follow: false },
};

type Params = { metric?: string; view?: string; entry?: string; state?: string };

function segLinkStyle(active: boolean): React.CSSProperties {
  return {
    fontSize: 12.5, padding: "7px 13px", borderRadius: 8, textDecoration: "none",
    border: `1px solid ${active ? "var(--eci-ink)" : "var(--rule)"}`,
    // The darkest step of the sequential ramp doubles as the active-segment fill — its foreground token
    // is already contrast-checked for both themes (PHASE3-SPEC.md §3.2), unlike a literal white.
    background: active ? "var(--eci-seq-5)" : "var(--card2)",
    color: active ? "var(--eci-seq-fg-5)" : "var(--ink2)",
  };
}

/** Three-metric segmented control in PHASE3-SPEC.md §3.1 is two here: PHASES-3-5-DECISIONS.md drops
 *  `appeals` as a tile measure ("one line removed from ECI_METRICS") — appeals stays on state pages only. */
function MetricSwitch({ current, view }: { current: string; view?: string }) {
  return (
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }} role="group" aria-label="Measure">
      {ECI_METRICS.map((m) => {
        const active = m.param === current;
        const params = new URLSearchParams({ metric: m.param });
        if (view) params.set("view", view);
        return (
          <Link key={m.param} href={`/eci-files/numbers?${params.toString()}`} aria-current={active ? "true" : undefined} className="seg tap" style={segLinkStyle(active)}>
            {m.shortLabel}
          </Link>
        );
      })}
    </div>
  );
}

function ViewToggle({ metric, view }: { metric: string; view?: string }) {
  const opts: { key: "tiles" | "table"; label: string }[] = [{ key: "tiles", label: "Tiles" }, { key: "table", label: "Table" }];
  return (
    <div style={{ display: "flex", gap: 6 }} role="group" aria-label="View">
      {opts.map((o) => {
        const isActive = view === o.key;
        const params = new URLSearchParams({ metric, view: o.key });
        return (
          <Link key={o.key} href={`/eci-files/numbers?${params.toString()}`} aria-current={isActive ? "true" : undefined} className="seg tap" style={segLinkStyle(isActive)}>
            {o.label}
          </Link>
        );
      })}
    </div>
  );
}

async function EntryDrawerBody({ id, preserve }: { id: string; preserve: Record<string, string | undefined> }) {
  const full = await getEciEntry(id).catch(() => null);
  if (!full) return null;
  return (
    <EntryDrawer>
      <EntryDetail entry={full} preserve={preserve} basePath="/eci-files/numbers" />
    </EntryDrawer>
  );
}

async function NumbersBody({ metric: metricParam, view, entry }: Params) {
  let overview: EciStatesOverview | null = null;
  try {
    overview = await getEciStates();
  } catch {
    overview = null;
  }

  if (!overview) {
    return (
      <p style={{ color: "var(--muted)", padding: "24px 4px" }}>
        The record hasn&apos;t loaded — try again in a moment.
      </p>
    );
  }

  const metric = eciMetricByParam(metricParam);

  return (
    <>
      <div style={{ marginBottom: 26 }}>
        <StatePicker regions={overview.regions} />
      </div>

      <NationalSummary national={overview.national} />
      <DraftCaveat lastAsOf={overview.last_as_of} />

      <div style={{ display: "flex", flexWrap: "wrap", gap: 14, alignItems: "center", justifyContent: "space-between", margin: "22px 0 16px" }}>
        <MetricSwitch current={metric.param} view={view} />
        <ViewToggle metric={metric.param} view={view} />
      </div>

      <div className="eci-numbers" data-view={view ?? "auto"}>
        <div className="eci-numbers-tiles">
          <StateTileGrid tiles={buildTileViewModels(overview.regions, metric)} groupLabel={metric.label} />
        </div>
        <div className="eci-numbers-table">
          <StateTable regions={overview.regions} metric={metric} />
        </div>
      </div>

      <StateTileLegend metric={metric} />
      <NationalPhaseBreakdown national={overview.national} />
      <HowWeCounted text={metric.howWeCounted} footnote={ECI_METRIC_FOOTNOTE} />

      {entry && (
        <Suspense fallback={null}>
          <EntryDrawerBody id={entry} preserve={{ metric: metric.param, view }} />
        </Suspense>
      )}
    </>
  );
}

export default async function EciNumbersPage({ searchParams }: { searchParams: Promise<Params> }) {
  const sp = await searchParams;

  // No-JS path for the state-picker form: `?state=` always redirects, never renders here.
  if (sp.state) {
    redirect(isEciRegionSlug(sp.state) ? `/eci-files/numbers/${sp.state}` : "/eci-files/numbers");
  }

  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 1000, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
        <SectionHero
          eyebrow="ECI FILES · THE NUMBERS"
          title="The SIR, state by state"
          backHref="/eci-files"
          backLabel="ECI Files"
          subtitle="Special Intensive Revision (SIR) figures for each State and Union Territory, taken from the cited entries in the record. The tiles are equal in size and placed roughly where the states sit; this is not a map. Pick a measure, or open a state to follow its roll from before the SIR to the final roll."
        />
        <Suspense fallback={<EciNumbersSkeleton />}>
          <NumbersBody metric={sp.metric} view={sp.view} entry={sp.entry} />
        </Suspense>
      </main>
    </>
  );
}
