import type { Metadata } from "next";
import { Suspense } from "react";
import { SiteHeader } from "@/components/SiteHeader";
import { ParliamentConsole, type Tab } from "@/components/parliament/ParliamentConsole";
import { ConsoleSkeleton } from "@/components/skeletons";
import {
  getParliamentStats, getParliamentTrends, getParliamentMinistries, getThemeFocus,
  type House, type MinistryCount,
} from "@/lib/api";

export const revalidate = 3600;
export const metadata: Metadata = {
  title: "Parliament functioning · Neta·Resume",
  description: "What the House is asking — questions by policy theme and ministry, trends, and party/state focus.",
};

const TABS: Tab[] = ["overview", "trends", "ministries", "parties", "states"];

async function safe<T>(p: Promise<T>): Promise<T | null> {
  try { return await p; } catch { return null; }
}

/** The data-heavy console: five parallel, independently-guarded fetches. Split into its own async
 *  component so the page shell (header + frame) streams to the browser first and this streams in when
 *  the fetches resolve, rather than the whole page blocking on the slowest of the five. */
async function ParliamentData({ house, initialTab, focus }: { house: House; initialTab: Tab; focus?: string }) {
  // Preload every tab's data in parallel so switching is instant (client-side, no refetch). Each is
  // ISR-cached and independently guarded — one failure only empties its own panel.
  const [stats, trends, ministries, parties, states] = await Promise.all([
    safe(getParliamentStats(house)),
    safe(getParliamentTrends(house)),
    safe(getParliamentMinistries(house)),
    safe(getThemeFocus("party", house)),
    safe(getThemeFocus("state", house)),
  ]);

  return (
    <ParliamentConsole
      house={house}
      initialTab={initialTab}
      focus={focus}
      stats={stats}
      trends={trends}
      ministries={(ministries as MinistryCount[]) ?? []}
      parties={parties}
      states={states}
    />
  );
}

export default async function ParliamentPage({ searchParams }: { searchParams: Promise<{ house?: string; tab?: string; focus?: string }> }) {
  const sp = await searchParams;
  const house: House = sp.house === "rs" ? "rs" : "ls";
  const initialTab: Tab = (TABS as string[]).includes(sp.tab ?? "") ? (sp.tab as Tab) : "overview";
  const focus = sp.focus;

  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 1120, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
        {/* key on house so switching houses re-shows the skeleton while the new house's data loads */}
        <Suspense key={house} fallback={<ConsoleSkeleton />}>
          <ParliamentData house={house} initialTab={initialTab} focus={focus} />
        </Suspense>
      </main>
    </>
  );
}
