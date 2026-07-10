"use client";

import { useState } from "react";
import Link from "next/link";
import { SectionHero } from "@/components/parliament/SectionHero";
import { SectionCard } from "@/components/parliament/SectionCard";
import { StatCard } from "@/components/parliament/StatCard";
import { HouseToggle } from "@/components/HouseToggle";
import { ParliamentSearchInput } from "@/components/ParliamentSearchInput";
import { Donut, ThemeStackedArea } from "@/components/resume/charts";
import { MinistryBars } from "@/components/MinistryBars";
import { AggregateLens } from "@/components/AggregateLens";
import { PhotoBox, Dot } from "@/components/ui";
import { themeColor } from "@/lib/themes";
import { photoSrc, type House, type ParliamentStats, type Trends, type MinistryCount, type ThemeFocusBreakdown } from "@/lib/api";

export type Tab = "overview" | "trends" | "ministries" | "parties" | "states";
const TABS: [Tab, string][] = [
  ["overview", "Overview"],
  ["trends", "Trends"],
  ["ministries", "Ministries"],
  ["parties", "Parties"],
  ["states", "States"],
];

const fmt = (n: number | undefined) => (n != null ? n.toLocaleString("en-IN") : "—");

/** URL for a given tab, preserving house/focus. Overview is the bare /parliament (no ?tab). */
function urlFor(tab: Tab, house: House, focus?: string): string {
  const p = new URLSearchParams();
  if (house === "rs") p.set("house", "rs");
  if (tab !== "overview") p.set("tab", tab);
  if (focus) p.set("focus", focus);
  const qs = p.toString();
  return `/parliament${qs ? `?${qs}` : ""}`;
}

export function ParliamentConsole({
  house, initialTab, focus, stats, trends, ministries, parties, states,
}: {
  house: House;
  initialTab: Tab;
  focus?: string;
  stats: ParliamentStats | null;
  trends: Trends | null;
  ministries: MinistryCount[];
  parties: ThemeFocusBreakdown | null;
  states: ThemeFocusBreakdown | null;
}) {
  const [tab, setTab] = useState<Tab>(initialTab);

  function go(next: Tab) {
    setTab(next);
    // Reflect the tab in the URL without a navigation/refetch, so refresh + the house toggle keep it.
    window.history.replaceState(null, "", urlFor(next, house, focus));
  }

  const houseLabel = house === "rs" ? "Rajya Sabha" : "18th Lok Sabha";
  const donut = (stats?.themes ?? []).map((t) => ({ label: t.theme, value: t.count, color: themeColor(t.theme) }));
  const topMinistry = stats?.top_ministries?.[0];

  return (
    <>
      <SectionHero
        eyebrow={`LIVE · ${house === "rs" ? "RAJYA SABHA" : "18TH LOK SABHA"}`}
        title="What the House is asking"
        right={<HouseToggle house={house} hrefLs={urlFor(tab, "ls", focus)} hrefRs={urlFor(tab, "rs", focus)} />}
      />

      {/* full-width search */}
      <div style={{ display: "flex", marginBottom: 22 }}>
        <ParliamentSearchInput big house={house === "rs" ? "rs" : undefined} />
      </div>

      {/* tab bar */}
      <div className="nr-xscroll" style={{ borderBottom: "1px solid var(--rule)", marginBottom: 24 }}>
        <div style={{ display: "flex", gap: 2, minWidth: "min-content" }}>
          {TABS.map(([key, label]) => {
            const active = key === tab;
            return (
              <button
                key={key}
                className="seg"
                onClick={() => go(key)}
                style={{
                  fontFamily: "'Bricolage Grotesque',sans-serif", fontSize: 14, fontWeight: 600, padding: "12px clamp(12px,3vw,20px)",
                  border: "none", background: "transparent", cursor: "pointer", marginBottom: -1, whiteSpace: "nowrap",
                  color: active ? "var(--ink)" : "var(--muted)",
                  borderBottom: `2px solid ${active ? "var(--accent)" : "transparent"}`,
                }}
              >
                {label}
              </button>
            );
          })}
        </div>
      </div>

      {/* panels */}
      <div className="fadeUp" key={tab}>
        {tab === "overview" && (
          !stats ? <Muted>Parliament data is loading…</Muted> : (
            <div style={{ display: "grid", gap: 14 }}>
              <div className="nr-statgrid">
                <StatCard tone="hero" icon="?" value={fmt(stats.total_questions)} label="Questions asked" />
                <StatCard icon="¶" value={fmt(stats.total_debates)} label="Debates participated in" />
                <StatCard icon="◍" value={fmt(stats.active_mps)} label="Members asking questions" />
              </div>
              <div className="nr-bento">
                <SectionCard className="col3" title="By policy area" source="MINISTRY MAP">
                  <p style={{ fontSize: 12.5, color: "var(--muted)", margin: "-4px 0 16px" }}>Share of questions across the seven policy themes.</p>
                  <Donut segments={donut} centerNum={fmt(stats.total_questions)} centerLabel="questions" size={150} />
                </SectionCard>
                <SectionCard className="col3" title="Most-questioned ministries" action="See all →" actionHref={urlFor("ministries", house, focus)}>
                  <p style={{ fontSize: 12.5, color: "var(--muted)", margin: "-4px 0 16px" }}>
                    Which departments the House scrutinises most{topMinistry ? <> — led by <strong style={{ color: "var(--ink2)", fontWeight: 600 }}>{topMinistry.ministry}</strong></> : null}.
                  </p>
                  <MinistryBars items={stats.top_ministries} />
                </SectionCard>
                <SectionCard className="col6" title="Most active members" source="PRS · DIGITAL SANSAD">
                  <p style={{ fontSize: 12.5, color: "var(--muted)", margin: "-4px 0 12px", maxWidth: "72ch" }}>
                    Top questioners this term. Missing ≠ inactive — rule-exempt members (ministers, the Speaker) don&rsquo;t table questions.
                  </p>
                  <div style={{ display: "grid" }}>
                    {stats.most_active.map((m, i) => (
                      <Link key={m.id} href={`/person/${m.id}`} className="tap nr-mprow" style={{ display: "flex", alignItems: "center", gap: 13, padding: "9px 8px", borderRadius: 10, textDecoration: "none", color: "var(--ink)", borderTop: i === 0 ? "none" : "1px solid var(--rule2)" }}>
                        <span className="mono" style={{ fontSize: 12, fontWeight: 600, color: i < 3 ? "var(--accent-2)" : "var(--faint)", width: 22, textAlign: "right", flexShrink: 0 }}>{i + 1}</span>
                        <PhotoBox w={32} h={38} src={photoSrc(m.id, m.photo_url)} />
                        <span className="nr-mprow-name" style={{ fontWeight: 500, fontSize: 14, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{m.display_name}</span>
                        <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 11.5, color: "var(--muted)", flexShrink: 0 }}>
                          <Dot color={themeColor(m.top_theme)} sq /><span className="nr-mprow-theme">{m.top_theme}</span>
                        </span>
                        <span className="mono" style={{ marginLeft: "auto", fontSize: 13.5, fontWeight: 600, flexShrink: 0 }}>{fmt(m.count)}<span style={{ color: "var(--muted)", fontWeight: 400 }}> Qs</span></span>
                      </Link>
                    ))}
                  </div>
                </SectionCard>
              </div>
            </div>
          )
        )}

        {tab === "trends" && (
          !trends || trends.months.length === 0 ? <Muted>Trends data is loading…</Muted> : (
            <>
              <TabHead title="Trends over time" desc={<>{houseLabel} questions by month, stacked by policy theme — how the House&rsquo;s attention shifted across the term ({fmt(trends.totals.reduce((n, v) => n + v, 0))} in all).</>} />
              <SectionCard><ThemeStackedArea months={trends.months} series={trends.series} /></SectionCard>
              <p style={{ fontSize: 12.5, color: "var(--muted)", margin: "16px 2px 0", maxWidth: "72ch" }}>
                Volume tracks the parliamentary calendar — peaks fall in the Budget (Feb–Mar) and Winter (Dec) sessions.
                Themes come from the ministry each question addressed. Missing ≠ zero: a quiet month is a recess, not disengagement.
              </p>
            </>
          )
        )}

        {tab === "ministries" && (
          ministries.length === 0 ? <Muted>No data.</Muted> : (
            <>
              <TabHead title="Ministries by questions" desc={<>Every Union ministry ranked by {houseLabel} questions ({fmt(ministries.reduce((n, m) => n + m.count, 0))} in all). Colours mark the policy theme; each links to the members who raise it.</>} />
              <SectionCard><MinistryBars items={ministries} /></SectionCard>
            </>
          )
        )}

        {tab === "parties" && (
          !parties || parties.groups.length === 0 ? <Muted>Party data is loading…</Muted> : (
            <>
              <TabHead title="What parties raise" desc={<>Each {houseLabel} party&rsquo;s questions by policy theme — the topics its members collectively emphasise. A descriptive comparison of focus; never a ranking of merit.</>} />
              <AggregateLens groups={parties.groups} kind="party" focus={focus} />
            </>
          )
        )}

        {tab === "states" && (
          !states || states.groups.length === 0 ? <Muted>State data is loading…</Muted> : (
            <>
              <TabHead title="What states raise" desc={<>Each state&rsquo;s {houseLabel} questions by policy theme — the topics its members collectively emphasise. A descriptive comparison of focus; never a ranking of merit.</>} />
              <AggregateLens groups={states.groups} kind="state" focus={focus} />
            </>
          )
        )}
      </div>
    </>
  );
}

function TabHead({ title, desc }: { title: string; desc: React.ReactNode }) {
  return (
    <div style={{ margin: "0 2px 18px" }}>
      <h2 className="serif" style={{ fontSize: "clamp(19px,3.5vw,23px)", fontWeight: 500, letterSpacing: "-0.015em", margin: "0 0 5px" }}>{title}</h2>
      <p style={{ fontSize: 14, color: "var(--ink2)", margin: 0, maxWidth: "68ch", lineHeight: 1.5 }}>{desc}</p>
    </div>
  );
}

function Muted({ children }: { children: React.ReactNode }) {
  return <p style={{ color: "var(--muted)", padding: "8px 2px" }}>{children}</p>;
}
