"use client";

import { useState } from "react";
import type { PersonResume, ParliamentaryQuestion, ThemeFocus } from "@/lib/api";
import { docSrc } from "@/lib/api";
import { rupees, severityMeta, year, pretty } from "@/lib/format";
import { Donut, WealthLine } from "@/components/resume/charts";
import { SourceLink, SourceChip, PendingFlag, SeverityBadge, PartyPill } from "@/components/ui";

const TABS = ["Overview", "Activity", "Questions", "Wealth", "Cases", "Career & Roles", "Contact", "In The News"] as const;
type Tab = (typeof TABS)[number];

function isRajyaSabha(resume: PersonResume): boolean {
  return resume.office_terms.some((o) => o.house.includes("Rajya Sabha"));
}

export function ProfileTabs({ resume }: { resume: PersonResume }) {
  const [tab, setTab] = useState<Tab>("Overview");
  // Hide the Activity tab for members with no PRS scorecard (former members, unmatched, RS with no data).
  const tabs = TABS.filter(
    (t) => (t !== "Activity" || resume.activity) && (t !== "Questions" || resume.parliamentary_record)
  );

  return (
    <>
      <div style={{ padding: "0 clamp(14px,4vw,40px)", borderBottom: "1px solid var(--rule)", background: "var(--card)" }}>
        <div style={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
          {tabs.map((t) => {
            const active = t === tab;
            return (
              <button
                key={t}
                className="seg"
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
        {tab === "Activity" && <Activity resume={resume} />}
        {tab === "Questions" && <Questions resume={resume} />}
        {tab === "Wealth" && <Wealth resume={resume} />}
        {tab === "Cases" && <Cases resume={resume} />}
        {tab === "Career & Roles" && <Career resume={resume} />}
        {tab === "Contact" && <ContactTab resume={resume} />}
        {tab === "In The News" && <News resume={resume} />}
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

const ACT_METRICS = [
  { key: "questions", label: "Questions asked" },
  { key: "debates", label: "Debates participated" },
  { key: "private_member_bills", label: "Private member's bills" },
] as const;

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
function isoDate(d: string | null | undefined): string {
  if (!d) return "";
  const [y, m, day] = d.slice(0, 10).split("-");
  const mi = parseInt(m, 10) - 1;
  return MONTHS[mi] ? `${parseInt(day, 10)} ${MONTHS[mi]} ${y}` : "";
}

function Activity({ resume }: { resume: PersonResume }) {
  const a = resume.activity;
  if (!a) return <Muted>No parliamentary activity data on record.</Muted>;
  const asOf = isoDate(a.period_end);
  return (
    <div className="fadeUp">
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 6 }}>
        <span style={headStyle}>Parliamentary activity — {a.house}</span>
        <span className="mono" style={{ fontSize: 11, color: "var(--faint)" }}>PRS MP TRACK</span>
      </div>
      <Muted>Cumulative over the term{asOf ? `, as of ${asOf}` : ""}. Bars compare this member against the {a.house} median.</Muted>
      <div style={{ display: "grid", gap: 12, marginTop: 16 }}>
        {ACT_METRICS.map((m) => <MetricBar key={m.key} label={m.label} metric={a[m.key]} />)}
      </div>
      <div style={{ marginTop: 16, display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        <SourceLink source={a.source} />
        <span className="mono" style={{ fontSize: 10, color: "var(--faint)" }}>Source: PRS Legislative Research (CC-BY 4.0)</span>
      </div>
    </div>
  );
}

function MetricBar({ label, metric }: { label: string; metric: { value: number | null; house_median?: number | null; percentile?: number | null } }) {
  const { value, house_median, percentile } = metric;
  if (value == null) {
    return (
      <div style={cardStyle}>
        <div style={{ ...headStyle, fontSize: 14 }}>{label}</div>
        <Muted>Not reported.</Muted>
      </div>
    );
  }
  const median = house_median ?? 0;
  const scale = Math.max(value, median * 2, 1);
  const above = median > 0 && value >= median;
  return (
    <div style={cardStyle}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 10 }}>
        <span style={{ ...headStyle, fontSize: 14 }}>{label}</span>
        <span className="mono" style={{ fontSize: 22, fontWeight: 700, color: "var(--ink)" }}>{value}</span>
      </div>
      <div style={{ position: "relative", height: 10, borderRadius: 6, background: "var(--rule)", overflow: "hidden" }}>
        <div style={{ position: "absolute", inset: 0, width: `${Math.min(100, (value / scale) * 100)}%`, background: above ? "var(--accent-2)" : "var(--accent-3)", borderRadius: 6 }} />
        {median > 0 && <div style={{ position: "absolute", top: -2, bottom: -2, left: `${Math.min(100, (median / scale) * 100)}%`, width: 2, background: "var(--ink)" }} title={`Median ${Math.round(median)}`} />}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 7 }}>
        <span style={{ fontSize: 12, color: "var(--muted)" }}>{house_median != null ? `House median ${Math.round(house_median)}` : ""}</span>
        {percentile != null && <span style={{ fontSize: 12, color: "var(--muted)" }}>Ahead of {percentile}% of the House</span>}
      </div>
    </div>
  );
}

function QARow({ title, date, meta, url }: { title: string; date?: string | null; meta: string; url?: string | null }) {
  return (
    <div style={cardStyle}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, marginBottom: 6 }}>
        <span style={{ ...headStyle, fontSize: 14, lineHeight: 1.35 }}>{title}</span>
        <span className="mono" style={{ fontSize: 11, color: "var(--muted)", whiteSpace: "nowrap" }}>{isoDate(date)}</span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        {meta && <span className="mono" style={{ fontSize: 11, color: "var(--faint)" }}>{meta}</span>}
        {url && <a href={url} target="_blank" rel="noreferrer" className="mono" style={{ fontSize: 11, color: "var(--accent-2)" }}>Official PDF ↗</a>}
      </div>
    </div>
  );
}

function CountChip({ n }: { n: number }) {
  return <span className="mono" style={{ fontSize: 12, color: "var(--accent-2)", background: "var(--accent-soft)", borderRadius: 20, padding: "2px 10px" }}>{n}</span>;
}

const THEME_COLORS: Record<string, string> = {
  "Economy & Industry": "var(--accent-2)",
  "Health": "var(--sev1)",
  "Education & Skills": "var(--sev2)",
  "Social Welfare & Justice": "var(--ok)",
  "Agriculture & Environment": "var(--accent-3)",
  "Infrastructure & Connectivity": "var(--accent)",
  "Governance & External": "var(--sev3)",
  "Other": "var(--muted)",
};

function themeColor(theme: string | null | undefined): string {
  return THEME_COLORS[theme ?? "Other"] ?? "var(--muted)";
}

// A single stacked bar of the theme mix; clicking a segment toggles the filter (synced with the chips).
function SegmentedBar({ focus, selected, onSelect }: { focus: ThemeFocus[]; selected: string | null; onSelect: (t: string | null) => void }) {
  return (
    <div style={{ display: "flex", height: 16, borderRadius: 8, overflow: "hidden", background: "var(--rule)" }}>
      {focus.map((t) => {
        const active = selected === null || selected === t.theme;
        return (
          <button key={t.theme} title={`${t.theme} — ${Math.round(t.share * 100)}%`} aria-label={`${t.theme} ${Math.round(t.share * 100)} percent`}
            onClick={() => onSelect(selected === t.theme ? null : t.theme)}
            style={{ width: `${t.share * 100}%`, background: themeColor(t.theme), opacity: active ? 1 : 0.28,
              border: "none", borderRight: "1px solid var(--card)", cursor: "pointer", padding: 0, transition: "opacity .2s" }} />
        );
      })}
    </div>
  );
}

function ThemeChip({ label, count, color, active, onClick }: { label: string; count: number; color?: string; active: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className="tap"
      style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12, padding: "4px 11px", borderRadius: 20, cursor: "pointer",
        border: `1px solid ${active ? "var(--accent)" : "var(--rule)"}`, background: active ? "var(--accent-soft)" : "var(--card)",
        color: active ? "var(--accent-soft-fg)" : "var(--ink2)" }}>
      {color && <span style={{ width: 8, height: 8, borderRadius: 8, background: color, display: "inline-block" }} />}
      {label} <span className="mono" style={{ color: active ? "var(--accent-soft-fg)" : "var(--muted)" }}>{count}</span>
    </button>
  );
}

function QuestionCard({ q }: { q: ParliamentaryQuestion }) {
  const reply = q.question_type === "Starred" ? "Oral reply" : q.question_type === "Unstarred" ? "Written reply" : "Reply";
  const meta = [q.theme, q.ministry].filter(Boolean).join(" · ");
  return (
    <div style={cardStyle} className="liftsm">
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, marginBottom: 8 }}>
        <span style={{ ...headStyle, fontSize: 14, lineHeight: 1.35 }}>{q.subject || "Question"}</span>
        <span className="mono" style={{ fontSize: 11, color: "var(--muted)", whiteSpace: "nowrap" }}>{isoDate(q.asked_date)}</span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <span style={{ display: "inline-flex", alignItems: "center", gap: 7, fontSize: 11, color: "var(--muted)" }}>
          <span style={{ width: 8, height: 8, borderRadius: 2, background: themeColor(q.theme), display: "inline-block" }} />
          {meta}
        </span>
        {q.document_url && (
          <a href={docSrc("question", q.id)} target="_blank" rel="noreferrer" className="btnGhost mono"
            style={{ fontSize: 11, padding: "3px 11px", borderRadius: 8, marginLeft: "auto" }}>
            {reply} →
          </a>
        )}
      </div>
    </div>
  );
}

function Questions({ resume }: { resume: PersonResume }) {
  const pr = resume.parliamentary_record;
  const [theme, setTheme] = useState<string | null>(null);
  if (!pr) return <Muted>No questions or debates on record.</Muted>;
  const sectionHead: React.CSSProperties = { ...headStyle, fontSize: 15, display: "flex", alignItems: "center", gap: 10, margin: "22px 0 12px" };
  const focus = pr.thematic_focus ?? [];
  const showFocus = pr.questions_count >= 8 && focus.length > 0;
  const shown = theme ? pr.questions.filter((q) => q.theme === theme) : pr.questions;
  const sel = theme ? focus.find((t) => t.theme === theme) : null;
  const ratio = sel && sel.house_share && sel.house_share > 0 ? sel.share / sel.house_share : null;
  return (
    <div className="fadeUp">
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 6 }}>
        <span style={headStyle}>Questions &amp; debates — {pr.house}</span>
        <span className="mono" style={{ fontSize: 11, color: "var(--faint)" }}>PRS · DIGITAL SANSAD</span>
      </div>
      <Muted>What this member raises in the House, by policy area — each links the official Lok Sabha reply.</Muted>

      {showFocus && (
        <>
          <div style={{ ...sectionHead, marginTop: 20 }}><span>Policy focus</span>
            <span className="mono" style={{ fontSize: 11, color: "var(--faint)", fontWeight: 400 }}>BY MINISTRY</span>
          </div>
          <SegmentedBar focus={focus} selected={theme} onSelect={setTheme} />
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 13 }}>
            <ThemeChip label="All" count={pr.questions_count} active={theme === null} onClick={() => setTheme(null)} />
            {focus.map((t) => (
              <ThemeChip key={t.theme} label={t.theme} count={t.count} color={themeColor(t.theme)}
                active={theme === t.theme} onClick={() => setTheme(theme === t.theme ? null : t.theme)} />
            ))}
          </div>
          {sel && (
            <div style={{ marginTop: 12 }}>
              <Muted>{sel.theme} — {Math.round(sel.share * 100)}% of questions{ratio ? ` · ${ratio.toFixed(1)}× the Lok Sabha average` : ""}.</Muted>
            </div>
          )}
        </>
      )}

      <div style={sectionHead}>
        <span>{theme ?? "Questions asked"}</span><CountChip n={shown.length} />
      </div>
      {shown.length === 0 ? <Muted>No questions in this area.</Muted> : (
        <div style={{ display: "grid", gap: 10 }}>
          {shown.map((q, i) => <QuestionCard key={i} q={q} />)}
        </div>
      )}
      {pr.questions_count > pr.questions.length && !theme && (
        <Muted>Showing {pr.questions.length} most recent of {pr.questions_count}.</Muted>
      )}

      <div style={sectionHead}><span>Debates participated in</span><CountChip n={pr.debates_count} /></div>
      {pr.debates.length === 0 ? <Muted>None listed.</Muted> : (
        <div style={{ display: "grid", gap: 10 }}>
          {pr.debates.map((d, i) => (
            <QARow key={i} title={d.title || "Debate"} date={d.debate_date} meta={d.debate_type || ""} url={d.document_url ? docSrc("debate", d.id) : null} />
          ))}
        </div>
      )}
      {pr.debates_count > pr.debates.length && (
        <Muted>Showing {pr.debates.length} most recent of {pr.debates_count}.</Muted>
      )}

      <div style={{ marginTop: 20, display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        <SourceLink source={pr.source} />
        <span className="mono" style={{ fontSize: 10, color: "var(--faint)" }}>Enumerated from PRS Legislative Research (CC-BY 4.0); documents © Lok Sabha Secretariat</span>
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
          // Prefer the named offence(s) from the catalog; fall back to the raw filing, then a generic label.
          const titles = [...new Set(c.sections.map((s) => s.title).filter(Boolean))];
          const charge = titles.length ? titles.join(", ") : (c.description || "Case");
          return (
            <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 14, padding: "18px 20px", borderBottom: i < cases.length - 1 ? "1px solid var(--rule2)" : "none" }}>
              <span style={{ width: 4, alignSelf: "stretch", borderRadius: 4, background: m.fg, flexShrink: 0 }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 9, flexWrap: "wrap" }}>
                  <span style={{ fontSize: 15, fontWeight: 600 }}>{charge}</span>
                  <span className="mono" style={{ fontSize: 10, fontWeight: 500, padding: "3px 8px", borderRadius: 5, background: m.bg, color: m.fg }}>{m.label}</span>
                </div>
                {c.sections.length > 0 && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
                    {c.sections.map((s, j) => (
                      <span key={j} className="mono" style={{ fontSize: 11, color: "var(--ink2)", background: "var(--sunken)", border: "1px solid var(--rule2)", borderRadius: 5, padding: "3px 8px" }}>
                        {s.raw}
                        {s.equivalent && <span style={{ color: "var(--faint)" }}> ≈ {s.equivalent}</span>}
                        {s.title && <span style={{ color: "var(--muted)" }}> · {s.title}</span>}
                      </span>
                    ))}
                  </div>
                )}
                {c.court && <div style={{ fontSize: 12, color: "var(--faint)", marginTop: 7 }}>{c.court}</div>}
              </div>
              <div style={{ textAlign: "right", flexShrink: 0 }}>
                <div className="mono" style={{ fontSize: 12, color: c.is_convicted ? "var(--sev1)" : "var(--ink2)", textTransform: "capitalize" }}>{c.status.replace("_", " ")}{c.filed_year ? ` · ${c.filed_year}` : ""}</div>
                <div style={{ marginTop: 7 }}><SourceLink source={c.source} /></div>
              </div>
            </div>
          );
        })}
      </div>
      <p style={{ fontSize: 12, color: "var(--muted)", marginTop: 12, lineHeight: 1.6 }}>
        ℹ The Indian Penal Code (IPC) was replaced by the Bharatiya Nyaya Sanhita (BNS) on 1 July 2024 — a
        renumbering of the law, not a change in what is alleged. Charges are shown with the section as filed;
        the equivalent section in the other code is shown where known (e.g. BNS 103 ≈ IPC 302), and severity
        is assessed the same way for both. Severity is derived from the offence, never adjudicated.
      </p>
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

const ROLE_LABEL: Record<string, string> = {
  prime_minister: "Prime Minister", chief_minister: "Chief Minister", deputy_cm: "Deputy Chief Minister",
  minister: "Minister", minister_state: "Minister of State", deputy_minister: "Deputy Minister",
  speaker: "Speaker", deputy_speaker: "Deputy Speaker", lop: "Leader of Opposition",
  leader_of_house: "Leader of the House", whip: "Whip", chief_whip: "Chief Whip",
  committee_chair: "Committee Chair", committee_member: "Committee Member",
  mayor: "Mayor", deputy_mayor: "Deputy Mayor", corporator: "Corporator",
};

function Positions({ resume }: { resume: PersonResume }) {
  const roles = resume.roles ?? [];
  if (!roles.length) return null;
  return (
    <div className="fadeUp" style={{ border: "1px solid var(--rule)", borderRadius: 12, background: "var(--card2)", padding: "clamp(18px,4vw,26px) clamp(16px,4vw,28px)", marginBottom: 18 }}>
      <div className="mono" style={{ fontSize: 11, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--faint)", marginBottom: 14 }}>Positions held</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {roles.map((r, i) => {
          const span = [r.start_date, r.end_date].filter(Boolean).map(year).join(" – ") || null;
          return (
            <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 12, flexWrap: "wrap" }}>
              <span className="mono" style={{ fontSize: 9.5, fontWeight: 600, letterSpacing: "0.05em", padding: "4px 9px", borderRadius: 5, background: "var(--accent-soft)", color: "var(--accent-soft-fg)", textTransform: "uppercase", flexShrink: 0 }}>
                {ROLE_LABEL[r.role_type] ?? r.role_type}
              </span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 9, flexWrap: "wrap" }}>
                  <span style={{ fontSize: 15, fontWeight: 600 }}>{r.title ?? r.portfolio ?? ROLE_LABEL[r.role_type] ?? r.role_type}</span>
                  {r.status === "current" && <span className="mono" style={{ fontSize: 9, fontWeight: 600, color: "var(--ok)" }}>● CURRENT</span>}
                  <SourceLink source={r.source} />
                </div>
                <div style={{ fontSize: 12.5, color: "var(--muted)", marginTop: 4 }}>
                  {[r.body, span].filter(Boolean).join(" · ")}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ContactTab({ resume }: { resume: PersonResume }) {
  const contacts = resume.contacts ?? [];
  if (!contacts.length) {
    return (
      <div className="fadeUp" style={{ padding: "28px 24px", border: "1px solid var(--rule)", borderRadius: 12, background: "var(--card2)" }}>
        <Muted>No official contact channels are on record for this legislator yet.</Muted>
      </div>
    );
  }
  const href = (c: { channel_type: string; value: string }) =>
    c.channel_type === "email" ? `mailto:${c.value}`
      : c.channel_type === "phone" ? `tel:${c.value.replace(/\s+/g, "")}`
      : c.channel_type === "website" || c.channel_type === "social" ? c.value
      : null;
  const ICON: Record<string, string> = { email: "✉", phone: "☎", website: "↗", social: "↗", office_address: "⌂", party_office: "⌂" };
  return (
    <div className="fadeUp">
      <div style={{ border: "1px solid var(--rule)", borderRadius: 12, overflow: "hidden", background: "var(--card2)" }}>
        {contacts.map((c, i) => {
          const link = href(c);
          const label = c.label ?? c.channel_type;
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 14, padding: "16px 20px", borderBottom: i < contacts.length - 1 ? "1px solid var(--rule2)" : "none" }}>
              <span style={{ fontSize: 16, color: "var(--accent)", width: 20, textAlign: "center", flexShrink: 0 }}>{ICON[c.channel_type] ?? "•"}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="mono" style={{ fontSize: 9.5, letterSpacing: "0.06em", textTransform: "uppercase", color: "var(--faint)", marginBottom: 3 }}>{label}</div>
                {link ? (
                  <a href={link} target={c.channel_type === "website" || c.channel_type === "social" ? "_blank" : undefined} rel="noopener noreferrer" style={{ fontSize: 14.5, color: "var(--accent)", textDecoration: "none", wordBreak: "break-all" }}>{c.value}</a>
                ) : (
                  <span style={{ fontSize: 14.5, color: "var(--ink)" }}>{c.value}</span>
                )}
              </div>
              <div style={{ flexShrink: 0 }}><SourceLink source={c.source} /></div>
            </div>
          );
        })}
      </div>
      <p style={{ fontSize: 12, color: "var(--muted)", marginTop: 12, lineHeight: 1.6 }}>
        ℹ Official channels only — the member&rsquo;s parliamentary office, official <span className="mono">@sansad.in</span> email and official profile, sourced from the Digital Sansad directory. Personal numbers and residential addresses are deliberately not listed.
      </p>
    </div>
  );
}

function Career({ resume }: { resume: PersonResume }) {
  const terms = resume.office_terms;
  return (
    <>
    <Positions resume={resume} />
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

function News({ resume }: { resume: PersonResume }) {
  const items = resume.news ?? [];
  if (!items.length) {
    return (
      <div className="fadeUp" style={{ display: "flex", alignItems: "center", gap: 12, padding: "28px 24px", border: "1px solid var(--rule)", borderRadius: 12, background: "var(--card2)" }}>
        <Muted>No recent news found for this legislator.</Muted>
      </div>
    );
  }
  return (
    <div className="fadeUp">
      <div style={{ border: "1px solid var(--rule)", borderRadius: 12, overflow: "hidden", background: "var(--card2)" }}>
        {items.map((a, i) => (
          <a
            key={i}
            href={a.url}
            target="_blank"
            rel="noopener noreferrer"
            className="liftsm"
            style={{ display: "block", textDecoration: "none", color: "var(--ink)", padding: "16px 20px", borderBottom: i < items.length - 1 ? "1px solid var(--rule2)" : "none" }}
          >
            <div style={{ fontSize: 15, fontWeight: 600, lineHeight: 1.35 }}>{a.title}</div>
            {a.snippet && (
              <div style={{ fontSize: 13, color: "var(--ink2)", marginTop: 6, lineHeight: 1.5 }}>{a.snippet}</div>
            )}
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8, flexWrap: "wrap" }}>
              {a.publisher && <span className="mono" style={{ fontSize: 11, fontWeight: 600, color: "var(--accent)" }}>{a.publisher}</span>}
              {a.published_at && <span style={{ fontSize: 11, color: "var(--muted)" }}>· {pretty(a.published_at)}</span>}
              <span className="mono" style={{ fontSize: 10, color: "var(--faint)", marginLeft: "auto" }}>↗ read</span>
            </div>
          </a>
        ))}
      </div>
      <div className="mono" style={{ fontSize: 10.5, color: "var(--faint)", marginTop: 12, lineHeight: 1.55, maxWidth: "80ch" }}>
        Auto-gathered from a public news search (Google News). Headlines link out to the publisher — this
        site doesn&rsquo;t host the articles, and an automated name search may occasionally surface an
        unrelated mention.
      </div>
    </div>
  );
}

function Muted({ children }: { children: React.ReactNode }) {
  return <span style={{ fontSize: 13, color: "var(--muted)" }}>{children}</span>;
}
