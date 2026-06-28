"use client";

import { useState } from "react";
import type { PersonResume } from "@/lib/api";
import { rupees, severityMeta, year, pretty } from "@/lib/format";
import { Donut, WealthLine } from "@/components/resume/charts";
import { SourceLink, SourceChip, PendingFlag, SeverityBadge, PartyPill } from "@/components/ui";

const TABS = ["Overview", "Wealth", "Cases", "Career & Party"] as const;
type Tab = (typeof TABS)[number];

function isRajyaSabha(resume: PersonResume): boolean {
  return resume.office_terms.some((o) => o.house.includes("Rajya Sabha"));
}

export function ProfileTabs({ resume }: { resume: PersonResume }) {
  const [tab, setTab] = useState<Tab>("Overview");

  return (
    <>
      <div style={{ padding: "0 clamp(14px,4vw,40px)", borderBottom: "1px solid var(--rule)", background: "var(--card)" }}>
        <div style={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
          {TABS.map((t) => {
            const active = t === tab;
            return (
              <button
                key={t}
                onClick={() => setTab(t)}
                style={{
                  fontFamily: "'Bricolage Grotesque',sans-serif", fontSize: 13.5, fontWeight: 600, padding: "14px clamp(11px,3vw,18px)",
                  border: "none", background: "transparent", cursor: "pointer", marginBottom: -1,
                  color: active ? "var(--ink)" : "var(--muted)",
                  borderBottom: `2px solid ${active ? "var(--accent)" : "transparent"}`,
                }}
              >
                {t}
              </button>
            );
          })}
        </div>
      </div>

      <div style={{ padding: "clamp(20px,4vw,30px) clamp(16px,4vw,40px) 40px", background: "var(--bg)" }}>
        {tab === "Overview" && <Overview resume={resume} />}
        {tab === "Wealth" && <Wealth resume={resume} />}
        {tab === "Cases" && <Cases resume={resume} />}
        {tab === "Career & Party" && <Career resume={resume} />}
      </div>
    </>
  );
}

function severityCounts(resume: PersonResume) {
  const c = { heinous: 0, serious: 0, minor: 0, unclassified: 0 };
  for (const k of resume.criminal_cases) {
    if (k.severity === "heinous") c.heinous++;
    else if (k.severity === "serious") c.serious++;
    else if (k.severity === "minor") c.minor++;
    else c.unclassified++;
  }
  return c;
}

function severityDonut(resume: PersonResume) {
  const c = severityCounts(resume);
  return [
    { label: "Heinous", value: c.heinous, color: "var(--sev1)" },
    { label: "Serious", value: c.serious, color: "var(--sev2)" },
    { label: "Minor", value: c.minor, color: "var(--sev3)" },
    { label: "Unclassified", value: c.unclassified, color: "var(--faint)" },
  ].filter((s) => s.value > 0);
}

function wealthPoints(resume: PersonResume) {
  return [...resume.wealth]
    .sort((a, b) => a.filed_year - b.filed_year)
    .map((w) => ({ label: w.election_cycle, value: w.total_assets }));
}

const cardStyle: React.CSSProperties = { minWidth: 0, border: "1px solid var(--rule)", borderRadius: 12, background: "var(--card2)", padding: "clamp(16px,4vw,24px)" };
const headStyle: React.CSSProperties = { fontFamily: "'Bricolage Grotesque',sans-serif", fontSize: 16, fontWeight: 600 };

function Overview({ resume }: { resume: PersonResume }) {
  const pts = wealthPoints(resume);
  const pending = resume.criminal_cases.filter((c) => !c.is_convicted).length;
  const donut = severityDonut(resume);
  return (
    <div className="fadeUp">
      <div className="nr-2col" style={{ ["--cols" as string]: "1.4fr 1fr", marginBottom: 18 }}>
        <div style={cardStyle}>
          <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 14 }}>
            <span style={headStyle}>Net assets, by cycle</span>
            <span className="mono" style={{ fontSize: 11, color: "var(--faint)" }}>ECI AFFIDAVITS</span>
          </div>
          {pts.length ? <WealthLine points={pts} /> : <Muted>No affidavit on record.</Muted>}
        </div>
        <div style={cardStyle}>
          <div style={{ ...headStyle, marginBottom: 14 }}>Cases by severity</div>
          {resume.criminal_cases.length ? (
            <Donut segments={donut} centerNum={pending} centerLabel="pending" size={104} />
          ) : resume.wealth.length ? (
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <SeverityBadge severity={null} total={0} />
              <Muted>No criminal cases declared.</Muted>
            </div>
          ) : (
            <Muted>No affidavit on record.</Muted>
          )}
        </div>
      </div>
    </div>
  );
}

function Wealth({ resume }: { resume: PersonResume }) {
  const rows = [...resume.wealth].sort((a, b) => b.filed_year - a.filed_year);
  const latest = rows[0];
  // Prefer the real movable/immovable split; fall back to net-worth vs liabilities.
  const hasSplit = latest && (latest.movable_assets != null || latest.immovable_assets != null);
  const composition = !latest
    ? []
    : hasSplit
    ? [
        { label: "Immovable", value: latest.immovable_assets ?? 0, color: "var(--accent-2)" },
        { label: "Movable", value: latest.movable_assets ?? 0, color: "var(--accent-3)" },
        { label: "Liabilities", value: latest.total_liabilities, color: "var(--sev2)" },
      ]
    : [
        { label: "Net worth", value: Math.max(latest.total_assets - latest.total_liabilities, 0), color: "var(--accent-2)" },
        { label: "Liabilities", value: latest.total_liabilities, color: "var(--sev2)" },
      ];
  return (
    <div className="fadeUp nr-2col" style={{ ["--cols" as string]: "1fr 1.3fr" }}>
      <div style={cardStyle}>
        <div style={{ ...headStyle, marginBottom: 18 }}>Latest composition</div>
        {latest ? (
          <Donut segments={composition} centerNum={rupees(latest.total_assets).replace("₹", "")} centerLabel="assets" size={128} />
        ) : (
          <Muted>No affidavit on record.</Muted>
        )}
      </div>
      <div style={{ minWidth: 0, border: "1px solid var(--rule)", borderRadius: 12, background: "var(--card2)", overflow: "hidden" }}>
        <div className="nr-xscroll">
        <div className="mono" style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr 1fr 1fr", padding: "13px 20px", background: "var(--sunken)", borderBottom: "1px solid var(--rule)", fontSize: 10, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--muted)" }}>
          <span>Cycle</span><span style={{ textAlign: "right" }}>Assets</span><span style={{ textAlign: "right" }}>Liabilities</span><span style={{ textAlign: "right" }}>Income</span>
        </div>
        {rows.map((r, i) => (
          <div key={i} style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr 1fr 1fr", padding: "15px 20px", borderBottom: "1px solid var(--rule2)", alignItems: "center" }}>
            <span style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <span style={{ fontSize: 13, fontWeight: 600 }}>{r.election_cycle}</span>
              <SourceLink source={r.source} />
            </span>
            <span className="mono" style={{ fontSize: 12.5, textAlign: "right", fontWeight: 600 }}>{rupees(r.total_assets)}</span>
            <span className="mono" style={{ fontSize: 12.5, textAlign: "right", color: "var(--ink2)" }}>{rupees(r.total_liabilities)}</span>
            <span className="mono" style={{ fontSize: 12.5, textAlign: "right", color: "var(--ink2)" }}>{r.self_income != null ? rupees(r.self_income) : "—"}</span>
          </div>
        ))}
        </div>
        <div className="mono" style={{ padding: "13px 20px", background: "var(--sunken)", fontSize: 10, color: "var(--accent)", letterSpacing: "0.06em" }}>
          ↗ EACH ROW LINKS TO THE SIGNED ECI AFFIDAVIT
        </div>
      </div>
    </div>
  );
}

function Cases({ resume }: { resume: PersonResume }) {
  const cases = resume.criminal_cases;
  const hasAffidavit = resume.wealth.length > 0;
  if (!cases.length) {
    return (
      <div className="fadeUp" style={{ display: "flex", alignItems: "center", gap: 12, padding: "28px 24px", border: "1px solid var(--rule)", borderRadius: 12, background: "var(--card2)" }}>
        {hasAffidavit ? (
          <>
            <SeverityBadge severity={null} total={0} />
            <Muted>No criminal cases declared in this affidavit.</Muted>
          </>
        ) : (
          <Muted>
            {isRajyaSabha(resume)
              ? "No ECI candidate affidavit is on record. Sitting Rajya Sabha members are indirectly elected and file no candidate affidavit, so declared cases are not available here."
              : "No ECI candidate affidavit has been matched for this member yet, so declared cases are not available here."}
          </Muted>
        )}
      </div>
    );
  }
  const convictions = cases.filter((c) => c.is_convicted).length;
  return (
    <div className="fadeUp">
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
        <PendingFlag>{convictions ? `${convictions} CONVICTION(S) ON RECORD` : "PENDING · UNPROVEN — NO CONVICTIONS ON RECORD"}</PendingFlag>
      </div>
      <div style={{ border: "1px solid var(--rule)", borderRadius: 12, overflow: "hidden", background: "var(--card2)" }}>
        {cases.map((c, i) => {
          const m = severityMeta(c.severity);
          const charge = c.description || c.sections.join(", ") || "Case";
          return (
            <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 14, padding: "18px 20px", borderBottom: i < cases.length - 1 ? "1px solid var(--rule2)" : "none" }}>
              <span style={{ width: 4, alignSelf: "stretch", borderRadius: 4, background: m.fg, flexShrink: 0 }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 9, flexWrap: "wrap" }}>
                  <span style={{ fontSize: 15, fontWeight: 600 }}>{charge}</span>
                  <span className="mono" style={{ fontSize: 10, fontWeight: 500, padding: "3px 8px", borderRadius: 5, background: m.bg, color: m.fg }}>{m.label}</span>
                </div>
                {c.sections.length > 0 && (
                  <div className="mono" style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 7 }}>{c.sections.join(" · ")}</div>
                )}
                {c.court && <div style={{ fontSize: 12, color: "var(--faint)", marginTop: 5 }}>{c.court}</div>}
              </div>
              <div style={{ textAlign: "right", flexShrink: 0 }}>
                <div className="mono" style={{ fontSize: 12, color: c.is_convicted ? "var(--sev1)" : "var(--ink2)", textTransform: "capitalize" }}>{c.status.replace("_", " ")}{c.filed_year ? ` · ${c.filed_year}` : ""}</div>
                <div style={{ marginTop: 7 }}><SourceLink source={c.source} /></div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function PartySwitches({ resume }: { resume: PersonResume }) {
  const switches = resume.party_switches ?? [];
  if (!switches.length) return null;
  return (
    <div className="fadeUp" style={{ border: "1px solid var(--rule)", borderRadius: 12, background: "var(--card2)", padding: "clamp(18px,4vw,24px) clamp(16px,4vw,26px)", marginBottom: 18 }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ ...headStyle, fontSize: 16 }}>Party changes — when &amp; why</span>
        <span className="mono" style={{ fontSize: 10, color: "var(--faint)", letterSpacing: "0.06em" }}>REPORTED · SOURCED</span>
      </div>
      <p style={{ fontSize: 12.5, color: "var(--muted)", margin: "0 0 18px", lineHeight: 1.5 }}>
        Detected from the public record. The reason is quoted from reporting — never inferred.
      </p>
      {switches.map((sw, i) => (
        <div key={i} style={{ display: "flex", gap: 16, marginBottom: i < switches.length - 1 ? 18 : 0 }}>
          <span style={{ width: 4, alignSelf: "stretch", borderRadius: 4, background: "var(--accent-2)", flexShrink: 0 }} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 9, flexWrap: "wrap" }}>
              <PartyPill party={sw.from_party} current={false} />
              <span style={{ color: "var(--faint)" }}>→</span>
              <PartyPill party={sw.to_party} />
              {sw.event_date && <span className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>{pretty(sw.event_date)}</span>}
            </div>
            {sw.narrative && (
              <p style={{ fontSize: 13.5, color: "var(--ink2)", lineHeight: 1.55, margin: "10px 0 0" }}>{sw.narrative}</p>
            )}
            {sw.source && (
              <div style={{ marginTop: 8 }}>
                <SourceChip source={sw.source} label={sw.source.name} />
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function Career({ resume }: { resume: PersonResume }) {
  const terms = resume.office_terms;
  return (
    <>
    <PartySwitches resume={resume} />
    <div className="fadeUp" style={{ border: "1px solid var(--rule)", borderRadius: 12, background: "var(--card2)", padding: "clamp(22px,4vw,32px) clamp(16px,4vw,30px)" }}>
      {terms.map((o, i) => {
        const span = [o.start_date, o.end_date].filter(Boolean).map(year).join("–") || `${o.house} ${o.cycle_number}`;
        return (
          <div key={i} style={{ display: "flex", gap: 20 }}>
            <div className="mono" style={{ fontSize: 11.5, color: "var(--muted)", width: "clamp(54px,14vw,104px)", flexShrink: 0, paddingTop: 2, textAlign: "right" }}>{span}</div>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0, width: 14 }}>
              <span style={{ width: 14, height: 14, borderRadius: "50%", background: "var(--accent-2)", border: "3px solid var(--card2)", boxShadow: "0 0 0 1px var(--border)", zIndex: 1, flexShrink: 0 }} />
              {i < terms.length - 1 && <span style={{ flex: 1, width: 2, background: "var(--rule)", minHeight: 18 }} />}
            </div>
            <div style={{ flex: 1, minWidth: 0, paddingBottom: 26 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                <span style={{ fontSize: 16, fontWeight: 600 }}>{o.house}{o.house.includes("Lok Sabha") && o.cycle_number ? ` · ${o.cycle_number}th` : ""}</span>
                <span className="mono" style={{ fontSize: 9.5, fontWeight: 600, letterSpacing: "0.06em", padding: "3px 9px", borderRadius: 5, background: "var(--accent-soft)", color: "var(--accent-soft-fg)", textTransform: "uppercase" }}>{o.status}</span>
                <SourceLink source={o.source} />
              </div>
              {(o.constituency ?? o.state) && <div style={{ fontSize: 13, color: "var(--muted)", marginTop: 5 }}>{o.constituency ?? o.state} · {o.membership_type}</div>}
              <div style={{ marginTop: 10 }}><PartyPill party={o.party} /></div>
            </div>
          </div>
        );
      })}
      <PartyNote resume={resume} />
    </div>
    </>
  );
}

function PartyNote({ resume }: { resume: PersonResume }) {
  const reasons = resume.party_history.some((p) => p.join_reason || p.leave_reason);
  return (
    <div style={{ marginTop: 4, paddingTop: 18, borderTop: "1px solid var(--rule2)", display: "flex", gap: 9, alignItems: "flex-start", fontSize: 11.5, color: "var(--muted)", lineHeight: 1.5 }}>
      <span className="mono" style={{ color: "var(--accent)", flexShrink: 0 }}>i</span>
      <span>
        The coloured node tracks the party label held in each office.{" "}
        {reasons
          ? "Where a switch is on record, the reason is quoted from the public record — never inferred."
          : "Where no reason for a switch is on public record, the field reads “no public reason on record.”"}
      </span>
    </div>
  );
}

function Muted({ children }: { children: React.ReactNode }) {
  return <span style={{ fontSize: 13, color: "var(--muted)" }}>{children}</span>;
}
