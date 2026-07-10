import type { Metadata } from "next";
import { SiteHeader } from "@/components/SiteHeader";
import { AggregateLens } from "@/components/AggregateLens";
import { HouseToggle } from "@/components/HouseToggle";
import { SectionHero } from "@/components/parliament/SectionHero";
import { getThemeFocus, type House, type ThemeFocusBreakdown } from "@/lib/api";

export const revalidate = 3600;
export const metadata: Metadata = {
  title: "By state · Parliament functioning · Neta·Resume",
  description: "What each state's MPs collectively raise in Parliament, by policy theme — a descriptive comparison of focus.",
};

export default async function StatesPage({ searchParams }: { searchParams: Promise<{ focus?: string; house?: string }> }) {
  const sp = await searchParams;
  const focus = sp.focus;
  const house: House = sp.house === "rs" ? "rs" : "ls";
  const hq = house === "rs" ? "?house=rs" : "";
  const houseLabel = house === "rs" ? "Rajya Sabha" : "18th Lok Sabha";
  let data: ThemeFocusBreakdown | null = null;
  try {
    data = await getThemeFocus("state", house);
  } catch { /* API not up yet */ }

  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 900, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
        <SectionHero
          eyebrow={`BY STATE · ${house === "rs" ? "RAJYA SABHA" : "18TH LOK SABHA"}`}
          title="What states raise"
          subtitle={<>Each state&rsquo;s {data?.house ?? houseLabel} questions, broken down by policy theme — the topics its members collectively emphasise. A descriptive comparison of focus, from the official record; never a ranking of merit.</>}
          backHref={`/parliament${hq}`}
          right={<HouseToggle house={house} hrefLs={`/parliament/states${focus ? `?focus=${encodeURIComponent(focus)}` : ""}`} hrefRs={`/parliament/states?house=rs${focus ? `&focus=${encodeURIComponent(focus)}` : ""}`} />}
        />

        {!data || data.groups.length === 0
          ? <p style={{ color: "var(--muted)" }}>State data is loading…</p>
          : <div className="fadeUp"><AggregateLens groups={data.groups} kind="state" focus={focus} /></div>}
      </main>
    </>
  );
}
