import type { Metadata } from "next";
import { SiteHeader } from "@/components/SiteHeader";
import { SectionHero } from "@/components/parliament/SectionHero";
import { StatCard } from "@/components/parliament/StatCard";
import { SectionCard } from "@/components/parliament/SectionCard";
import { SourceLink } from "@/components/ui";
import { IndicatorLine } from "@/components/resume/charts";
import { getIndiaDashboard, type IndiaDashboard, type IndicatorSeries } from "@/lib/api";
import { indicatorValue } from "@/lib/format";

export const revalidate = 3600;
export const metadata: Metadata = {
  title: "India Dashboard · Neta·Resume",
  description:
    "The country's own numbers — GDP, prices, work, health, education, environment — from official statistics, every figure linked to its source.",
};

// The four headline series pinned above the fold (all near-current, yearly World Bank values).
const HERO: [string, string][] = [
  ["NY.GDP.MKTP.CD", "GDP"],
  ["NY.GDP.MKTP.KD.ZG", "GDP growth"],
  ["FP.CPI.TOTL.ZG", "Inflation (CPI)"],
  ["SL.UEM.TOTL.ZS", "Unemployment"],
];

function findSeries(dash: IndiaDashboard, code: string): IndicatorSeries | null {
  for (const c of dash.categories) for (const i of c.indicators) if (i.code === code) return i;
  return null;
}

/** One indicator tile: name, latest value + its year (series lag differs), trend, unit + source link. */
function IndicatorTile({ ind }: { ind: IndicatorSeries }) {
  return (
    <div style={{ border: "1px solid var(--rule)", borderRadius: 12, background: "var(--card)", padding: "14px 14px 10px", minWidth: 0, display: "flex", flexDirection: "column" }}>
      <div style={{ fontSize: 12.5, color: "var(--ink2)", lineHeight: 1.35, minHeight: "2.7em" }}>{ind.name}</div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 7, margin: "6px 0 4px" }}>
        <span className="mono" style={{ fontSize: 21, fontWeight: 700 }}>{indicatorValue(ind.latest_value, ind.format)}</span>
        <span className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>as of {ind.latest_year}</span>
      </div>
      <IndicatorLine points={ind.points} format={ind.format} />
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, marginTop: 8, paddingTop: 8, borderTop: "1px solid var(--rule)" }}>
        <span style={{ fontSize: 10.5, color: "var(--faint)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{ind.unit}</span>
        <SourceLink source={ind.source} />
      </div>
    </div>
  );
}

export default async function IndiaPage() {
  let dash: IndiaDashboard | null = null;
  try {
    dash = await getIndiaDashboard();
  } catch {
    dash = null;
  }
  const empty = !dash || dash.categories.length === 0;
  const hero = empty ? [] : HERO.map(([code, label]) => ({ label, ind: findSeries(dash!, code) }));

  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 1120, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
        <SectionHero
          eyebrow="INDIA · OFFICIAL DATA"
          title="India Dashboard"
          subtitle={
            <>
              The country&apos;s own numbers — GDP, prices, work, health, education, environment — so the data the
              government puts out is one click from its source. Official statistics via the World Bank&apos;s open
              data; descriptive, never a judgment.
            </>
          }
        />

        {empty ? (
          <SectionCard>
            <div style={{ textAlign: "center", padding: "34px 12px", color: "var(--muted)", fontSize: 14 }}>
              The dashboard hasn&apos;t been populated yet — indicator data lands with the next ingestion run.
            </div>
          </SectionCard>
        ) : (
          <>
            <div className="nr-statgrid" style={{ marginBottom: 26 }}>
              {hero.map(({ label, ind }) => (
                <StatCard
                  key={label}
                  value={ind ? indicatorValue(ind.latest_value, ind.format) : "—"}
                  label={label}
                  hint={ind ? `as of ${ind.latest_year} · World Bank` : "not on record"}
                  tone={label === "GDP" ? "hero" : "default"}
                />
              ))}
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
              {dash!.categories.map((cat) => (
                <SectionCard key={cat.name} title={cat.name} source="WORLD BANK · CC-BY 4.0 · TIER 1">
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(min(250px, 100%), 1fr))", gap: 12 }}>
                    {cat.indicators.map((ind) => (
                      <IndicatorTile key={ind.code} ind={ind} />
                    ))}
                  </div>
                </SectionCard>
              ))}
            </div>

            <p style={{ fontSize: 12, color: "var(--muted)", lineHeight: 1.6, marginTop: 22, maxWidth: "88ch" }}>
              Every series above is fetched from the{" "}
              <a href="https://data.worldbank.org/country/india" target="_blank" rel="noopener noreferrer" style={{ color: "var(--accent-2)" }}>
                World Bank Open Data API
              </a>{" "}
              (
              <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener noreferrer" style={{ color: "var(--accent-2)" }}>
                CC-BY 4.0
              </a>
              ), which compiles official Indian and international statistics. Series lag differs — GDP and prices are
              near-current, while survey-based series (poverty, the Gini, literacy) update only in survey years; each
              value states the year it is &ldquo;as of&rdquo;. Years a source hasn&apos;t published are simply absent from a
              chart — missing data is never shown as zero.
            </p>
          </>
        )}
      </main>
    </>
  );
}
