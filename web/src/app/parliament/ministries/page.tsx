import type { Metadata } from "next";
import { SiteHeader } from "@/components/SiteHeader";
import { MinistryBars } from "@/components/MinistryBars";
import { HouseToggle } from "@/components/HouseToggle";
import { SectionHero } from "@/components/parliament/SectionHero";
import { SectionCard } from "@/components/parliament/SectionCard";
import { getParliamentMinistries, type House, type MinistryCount } from "@/lib/api";

export const revalidate = 3600;
export const metadata: Metadata = {
  title: "Ministries by questions · Parliament functioning · Neta·Resume",
  description: "Every Union ministry ranked by the number of parliamentary questions it fielded.",
};

export default async function MinistriesPage({ searchParams }: { searchParams: Promise<{ house?: string }> }) {
  const house: House = (await searchParams).house === "rs" ? "rs" : "ls";
  const hq = house === "rs" ? "?house=rs" : "";
  const houseLabel = house === "rs" ? "Rajya Sabha" : "18th Lok Sabha";
  let items: MinistryCount[] = [];
  try {
    items = await getParliamentMinistries(house);
  } catch { /* API not up yet */ }
  const total = items.reduce((n, m) => n + m.count, 0);

  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 860, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
        <SectionHero
          eyebrow={`MINISTRIES · ${house === "rs" ? "RAJYA SABHA" : "18TH LOK SABHA"}`}
          title="Ministries by questions"
          subtitle={<>Every Union ministry ranked by {houseLabel} questions ({total.toLocaleString("en-IN")} in all). Colours mark the policy theme; each links to the members who raise it.</>}
          backHref={`/parliament${hq}`}
          right={<HouseToggle house={house} hrefLs="/parliament/ministries" hrefRs="/parliament/ministries?house=rs" />}
        />
        {items.length === 0
          ? <p style={{ color: "var(--muted)" }}>No data.</p>
          : <div className="fadeUp"><SectionCard><MinistryBars items={items} /></SectionCard></div>}
      </main>
    </>
  );
}
