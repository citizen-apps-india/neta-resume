import type { Metadata } from "next";
import { SiteHeader } from "@/components/SiteHeader";
import { ParliamentConsole, type Tab } from "@/components/parliament/ParliamentConsole";
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

export default async function ParliamentPage({ searchParams }: { searchParams: Promise<{ house?: string; tab?: string; focus?: string }> }) {
  const sp = await searchParams;
  const house: House = sp.house === "rs" ? "rs" : "ls";
  const initialTab: Tab = (TABS as string[]).includes(sp.tab ?? "") ? (sp.tab as Tab) : "overview";
  const focus = sp.focus;

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
    <>
      <SiteHeader />
      <main style={{ maxWidth: 1120, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
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
      </main>
    </>
  );
}
