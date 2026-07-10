import type { Metadata } from "next";
import { SiteHeader } from "@/components/SiteHeader";
import { Donut } from "@/components/resume/charts";
import { MinistryBars } from "@/components/MinistryBars";
import { HouseToggle } from "@/components/HouseToggle";
import { SectionHero } from "@/components/parliament/SectionHero";
import { StatCard } from "@/components/parliament/StatCard";
import { SectionCard } from "@/components/parliament/SectionCard";
import { NavCard } from "@/components/parliament/NavCard";
import { PhotoBox, Dot } from "@/components/ui";
import Link from "next/link";
import { themeColor } from "@/lib/themes";
import { getParliamentStats, photoSrc, type House, type ParliamentStats } from "@/lib/api";

export const revalidate = 3600;
export const metadata: Metadata = {
  title: "Parliament functioning · Neta·Resume",
  description: "What the House is asking — questions by policy theme and ministry, and the most active members.",
};

const fmt = (n: number | undefined) => (n != null ? n.toLocaleString("en-IN") : "—");

export default async function ParliamentPage({ searchParams }: { searchParams: Promise<{ house?: string }> }) {
  const house: House = (await searchParams).house === "rs" ? "rs" : "ls";
  const hq = house === "rs" ? "?house=rs" : "";
  const houseLabel = house === "rs" ? "Rajya Sabha" : "18th Lok Sabha";
  let s: ParliamentStats | null = null;
  try {
    s = await getParliamentStats(house);
  } catch { /* API not up yet */ }

  const themes = s?.themes ?? [];
  const donut = themes.map((t) => ({ label: t.theme, value: t.count, color: themeColor(t.theme) }));
  const topMinistry = s?.top_ministries?.[0];

  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 1120, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
        <SectionHero
          eyebrow={`LIVE · ${house === "rs" ? "RAJYA SABHA" : "18TH LOK SABHA"}`}
          title="What the House is asking"
          subtitle={<>The {s?.house ?? houseLabel}, seen through its parliamentary questions — by policy area and ministry, and the members driving it. Every figure is read live from the official record.</>}
          right={<HouseToggle house={house} hrefLs="/parliament" hrefRs="/parliament?house=rs" />}
        />

        {!s ? (
          <p style={{ color: "var(--muted)" }}>Parliament data is loading…</p>
        ) : (
          <div className="fadeUp" style={{ display: "grid", gap: 14 }}>
            {/* headline stats */}
            <div className="nr-statgrid">
              <StatCard tone="hero" icon="?" value={fmt(s.total_questions)} label="Questions asked" />
              <StatCard icon="¶" value={fmt(s.total_debates)} label="Debates participated in" />
              <StatCard icon="◍" value={fmt(s.active_mps)} label="Members asking questions" />
            </div>

            {/* explore nav */}
            <div className="nr-navgrid">
              <NavCard href={`/parliament/search${hq}`} icon="⌕" label="Search the record" desc="Questions & debates" />
              <NavCard href={`/parliament/trends${hq}`} icon="↗" label="Trends over time" desc="Month by month" />
              <NavCard href={`/parliament/parties${hq}`} icon="▦" label="By party" desc="What parties raise" />
              <NavCard href={`/parliament/states${hq}`} icon="◈" label="By state" desc="What states raise" />
            </div>

            {/* bento: policy mix + ministries */}
            <div className="nr-bento">
              <SectionCard className="col3" title="By policy area" source="MINISTRY MAP">
                <p style={{ fontSize: 12.5, color: "var(--muted)", margin: "-4px 0 16px" }}>Share of questions across the seven policy themes.</p>
                <Donut segments={donut} centerNum={fmt(s.total_questions)} centerLabel="questions" size={150} />
              </SectionCard>

              <SectionCard className="col3" title="Most-questioned ministries" action="See all →" actionHref={`/parliament/ministries${hq}`}>
                <p style={{ fontSize: 12.5, color: "var(--muted)", margin: "-4px 0 16px" }}>
                  Which departments the House scrutinises most{topMinistry ? <> — led by <strong style={{ color: "var(--ink2)", fontWeight: 600 }}>{topMinistry.ministry}</strong></> : null}.
                </p>
                <MinistryBars items={s.top_ministries} />
              </SectionCard>

              {/* most active members */}
              <SectionCard className="col6" title="Most active members" source="PRS · DIGITAL SANSAD">
                <p style={{ fontSize: 12.5, color: "var(--muted)", margin: "-4px 0 12px", maxWidth: "72ch" }}>
                  Top questioners this term. Missing ≠ inactive — rule-exempt members (ministers, the Speaker) don&rsquo;t table questions.
                </p>
                <div style={{ display: "grid" }}>
                  {s.most_active.map((m, i) => (
                    <Link key={m.id} href={`/person/${m.id}`} className="tap" style={{ display: "flex", alignItems: "center", gap: 13, padding: "9px 8px", borderRadius: 10, textDecoration: "none", color: "var(--ink)", borderTop: i === 0 ? "none" : "1px solid var(--rule2)" }}>
                      <span className="mono" style={{ fontSize: 12, fontWeight: 600, color: i < 3 ? "var(--accent-2)" : "var(--faint)", width: 22, textAlign: "right", flexShrink: 0 }}>{i + 1}</span>
                      <PhotoBox w={32} h={38} src={photoSrc(m.id, m.photo_url)} />
                      <span style={{ fontWeight: 500, fontSize: 14, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{m.display_name}</span>
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 11.5, color: "var(--muted)", flexShrink: 0 }}>
                        <Dot color={themeColor(m.top_theme)} sq />{m.top_theme}
                      </span>
                      <span className="mono" style={{ marginLeft: "auto", fontSize: 13.5, fontWeight: 600, flexShrink: 0 }}>{fmt(m.count)}<span style={{ color: "var(--muted)", fontWeight: 400 }}> Qs</span></span>
                    </Link>
                  ))}
                </div>
              </SectionCard>
            </div>
          </div>
        )}
      </main>
    </>
  );
}
