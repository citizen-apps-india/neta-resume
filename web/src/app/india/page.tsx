import type { Metadata } from "next";
import { Suspense } from "react";
import { SiteHeader } from "@/components/SiteHeader";
import { SectionHero } from "@/components/parliament/SectionHero";
import { SectionCard } from "@/components/parliament/SectionCard";
import { DashboardBodySkeleton } from "@/components/skeletons";
import { SourceLink } from "@/components/ui";
import { IndicatorLine } from "@/components/resume/charts";
import { CategoryRail } from "@/components/india/CategoryRail";
import { getIndiaDashboard, type IndiaDashboard, type IndicatorSeries } from "@/lib/api";
import { indicatorValue, indicatorChange } from "@/lib/format";

export const revalidate = 3600;
export const metadata: Metadata = {
  title: "India Dashboard · Neta·Resume",
  description:
    "The country's own numbers — GDP, prices, work, health, education, public institutions — from official statistics, every figure linked to its source.",
};

// The four headline series pinned above the fold (all near-current, yearly World Bank values).
const HERO: [string, string][] = [
  ["NY.GDP.MKTP.CD", "GDP"],
  ["NY.GDP.MKTP.KD.ZG", "GDP growth"],
  ["FP.CPI.TOTL.ZG", "Inflation (CPI)"],
  ["SL.UEM.TOTL.ZS", "Unemployment"],
];

const slug = (name: string) => "sec-" + name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");

function findSeries(dash: IndiaDashboard, code: string): IndicatorSeries | null {
  for (const c of dash.categories) for (const i of c.indicators) if (i.code === code) return i;
  return null;
}

/** A good/bad-aware year-on-year change chip (▲/▼ %). Renders nothing for single-point series. */
function ChangeChip({ ind }: { ind: IndicatorSeries }) {
  const chg = indicatorChange(ind.points, ind.polarity);
  if (!chg) return null;
  return <span className={`nr-chg nr-chg-${chg.tone}`}>{chg.text}</span>;
}

/** One indicator tile: name, latest value + change chip + its year, trend (when ≥2 points), unit + source.
 *  `prominent` gives the hero row a bigger value and an accent frame; the first hero tile a full wash. */
function IndicatorTile({ ind, prominent = false, hero = false, label }: {
  ind: IndicatorSeries; prominent?: boolean; hero?: boolean; label?: string;
}) {
  const multi = ind.points.length >= 2;
  return (
    <div
      className={`nr-ind-tile${prominent ? " prominent" : ""}${hero ? " hero" : ""}`}
      style={{ borderRadius: prominent ? 14 : 12 }}
    >
      <div className="nr-ind-name" style={{ minHeight: prominent ? undefined : "2.7em" }}>{label ?? ind.name}</div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap", margin: "6px 0 4px" }}>
        <span className="mono nr-ind-value" style={{ fontSize: prominent ? "clamp(23px,4.2vw,30px)" : 21 }}>
          {indicatorValue(ind.latest_value, ind.format)}
        </span>
        <ChangeChip ind={ind} />
        <span className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>as of {ind.latest_year}</span>
      </div>
      {multi ? (
        <IndicatorLine points={ind.points} format={ind.format} />
      ) : (
        ind.note && <div className="nr-ind-note">{ind.note}</div>
      )}
      <div className="nr-ind-foot">
        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{ind.unit}</span>
        <SourceLink source={ind.source} />
      </div>
    </div>
  );
}

/** The dashboard payload (~24 series × history) and everything derived from it. Split into its own async
 *  component so the static SectionHero paints immediately and this streams in below it once the (ISR-cached)
 *  dashboard resolves — a cold render no longer blanks the whole page. */
async function IndiaBody() {
  let dash: IndiaDashboard | null = null;
  try {
    dash = await getIndiaDashboard();
  } catch {
    dash = null;
  }
  const empty = !dash || dash.categories.length === 0;
  const hero = empty ? [] : HERO.map(([code, label]) => ({ label, ind: findSeries(dash!, code) }));
  const railItems = empty ? [] : dash!.categories.map((c) => ({ name: c.name, slug: slug(c.name) }));
  const updatedYear = empty
    ? 0
    : Math.max(...dash!.categories.flatMap((c) => c.indicators.map((i) => i.latest_year)));

  return (
    <>
      {empty ? (
          <SectionCard>
            <div style={{ textAlign: "center", padding: "34px 12px", color: "var(--muted)", fontSize: 14 }}>
              The dashboard hasn&apos;t been populated yet — indicator data lands with the next ingestion run.
            </div>
          </SectionCard>
        ) : (
          <>
            <div className="nr-fresh-row">
              <span className="mono nr-fresh">
                <span className="pulse-dot" /> Updated {updatedYear} · Tier&nbsp;1 official
              </span>
            </div>
            <div className="nr-statgrid" style={{ marginBottom: 22 }}>
              {hero.map(({ label, ind }, i) =>
                ind ? (
                  <IndicatorTile key={label} ind={ind} prominent hero={i === 0} label={label} />
                ) : (
                  <div key={label} className="nr-ind-tile prominent" style={{ borderRadius: 14 }}>
                    <div className="nr-ind-name">{label}</div>
                    <div className="mono nr-ind-value" style={{ fontSize: "clamp(23px,4.2vw,30px)" }}>—</div>
                    <div className="nr-ind-note">not on record</div>
                  </div>
                ),
              )}
            </div>

            <CategoryRail items={railItems} />

            <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
              {dash!.categories.map((cat) => (
                <section key={cat.name} id={slug(cat.name)} className="nr-dash-section">
                  <SectionCard title={cat.name} source={`OFFICIAL · TIER ${cat.indicators[0]?.source.trust_tier ?? 1}`}>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(min(250px, 100%), 1fr))", gap: 12 }}>
                      {cat.indicators.map((ind) => (
                        <IndicatorTile key={ind.code} ind={ind} />
                      ))}
                    </div>
                  </SectionCard>
                </section>
              ))}
            </div>

            <p style={{ fontSize: 12, color: "var(--muted)", lineHeight: 1.6, marginTop: 22, maxWidth: "88ch" }}>
              Economic and demographic series come from the{" "}
              <a href="https://data.worldbank.org/country/india" target="_blank" rel="noopener noreferrer" style={{ color: "var(--accent-2)" }}>
                World Bank Open Data API
              </a>{" "}
              (
              <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener noreferrer" style={{ color: "var(--accent-2)" }}>
                CC-BY 4.0
              </a>
              ); the public-institution counts (schools, hospitals, colleges, police, and more) are transcribed
              from official Indian government reports — each tile links to its source and states the year it is
              &ldquo;as of&rdquo;. Series lag differs, and years a source hasn&apos;t published are simply absent from a
              chart — missing data is never shown as zero.
            </p>
          </>
        )}
    </>
  );
}

export default function IndiaPage() {
  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 1120, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
        <SectionHero
          eyebrow="INDIA · OFFICIAL DATA"
          title="India Dashboard"
          subtitle={
            <>
              The country&apos;s own numbers — GDP, prices, work, health, education, and the public institutions
              that run it — so the data the government puts out is one click from its source. Descriptive,
              sourced, never a judgment.
            </>
          }
        />
        <Suspense fallback={<DashboardBodySkeleton />}>
          <IndiaBody />
        </Suspense>
      </main>
    </>
  );
}
