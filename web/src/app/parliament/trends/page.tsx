import type { Metadata } from "next";
import { SiteHeader } from "@/components/SiteHeader";
import { ThemeStackedArea } from "@/components/resume/charts";
import { HouseToggle } from "@/components/HouseToggle";
import { SectionHero } from "@/components/parliament/SectionHero";
import { SectionCard } from "@/components/parliament/SectionCard";
import { getParliamentTrends, type House, type Trends } from "@/lib/api";

export const revalidate = 3600;
export const metadata: Metadata = {
  title: "Trends over time · Parliament functioning · Neta·Resume",
  description: "How the House's attention shifted month to month across the seven policy themes.",
};

export default async function TrendsPage({ searchParams }: { searchParams: Promise<{ house?: string }> }) {
  const house: House = (await searchParams).house === "rs" ? "rs" : "ls";
  const hq = house === "rs" ? "?house=rs" : "";
  const houseLabel = house === "rs" ? "Rajya Sabha" : "18th Lok Sabha";
  let t: Trends | null = null;
  try {
    t = await getParliamentTrends(house);
  } catch { /* API not up yet */ }

  const total = t?.totals.reduce((n, v) => n + v, 0) ?? 0;

  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 1120, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
        <SectionHero
          eyebrow={`TRENDS · ${house === "rs" ? "RAJYA SABHA" : "18TH LOK SABHA"}`}
          title="Trends over time"
          subtitle={<>{t?.house ?? houseLabel} questions by month, stacked by policy theme — how the House&rsquo;s attention shifted across the term{total ? <> ({total.toLocaleString("en-IN")} questions in all)</> : null}.</>}
          backHref={`/parliament${hq}`}
          right={<HouseToggle house={house} hrefLs="/parliament/trends" hrefRs="/parliament/trends?house=rs" />}
        />

        {!t || t.months.length === 0 ? (
          <p style={{ color: "var(--muted)" }}>Trends data is loading…</p>
        ) : (
          <div className="fadeUp">
            <SectionCard>
              <ThemeStackedArea months={t.months} series={t.series} />
            </SectionCard>
            <p style={{ fontSize: 12.5, color: "var(--muted)", margin: "16px 2px 0", maxWidth: "72ch" }}>
              Volume tracks the parliamentary calendar — peaks fall in the Budget (Feb–Mar) and Winter (Dec) sessions,
              with near-zero months when the House isn&rsquo;t sitting. Themes come from the ministry each question
              addressed. Missing ≠ zero: a quiet month is a recess, not disengagement.
            </p>
          </div>
        )}
      </main>
    </>
  );
}
