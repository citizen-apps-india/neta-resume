import Link from "next/link";
import { countIndian } from "@/lib/format";
import { StatusChip } from "@/components/eci-files/StatusChip";
import { eciEntryHref, formatLooseDate } from "@/lib/eci-files";
import type { EciNationalFigure, EciNationalGroup } from "@/types/eci-files";

const PHASE_TITLE: Partial<Record<EciNationalGroup, string>> = {
  phase_1: "Phase I · Bihar",
  phase_2: "Phase II · 12 States/UTs",
};

function SourceTag({ f, basePath }: { f: EciNationalFigure; basePath: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
      {f.as_of && <span className="mono" style={{ fontSize: 10.5, color: "var(--faint)" }}>{formatLooseDate(f.as_of)}</span>}
      <Link href={eciEntryHref(f.source_entry_id, {}, basePath)} className="mono" style={{ fontSize: 10.5, color: "var(--accent-2)", textDecoration: "none" }}>
        {f.computed ? "Inputs:" : "Source:"} {f.source_entry_title}
      </Link>
      {f.computed ? (
        <span
          className="mono"
          style={{
            display: "inline-flex", alignItems: "center", fontSize: 10.5, fontWeight: 600,
            letterSpacing: "0.02em", padding: "3px 9px", borderRadius: 999,
            border: "1px solid var(--border2)", color: "var(--ink2)", background: "var(--sunken)",
          }}
        >
          Our computation
        </span>
      ) : (
        <StatusChip status={f.source_status} />
      )}
    </div>
  );
}

function FigureRow({ f, basePath }: { f: EciNationalFigure; basePath: string }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div className="mono" style={{ fontSize: 15, fontWeight: 700, color: "var(--eci-ink)", lineHeight: 1.1 }}>
        {f.approx ? "≈" : ""}{countIndian(f.electors)}
      </div>
      <div style={{ fontSize: 12, color: "var(--ink2)", margin: "2px 0" }}>{f.label}</div>
      <SourceTag f={f} basePath={basePath} />
      {f.note && <div style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 4, maxWidth: "68ch" }}>{f.note}</div>}
    </div>
  );
}

/** The hero's headline card (docs/eci-files/designs/B-After-Numbers.dc.html): ONE cited national figure
 *  ("all" group, not computed), big — a computed alternative (our own sum, where ECI has published none)
 *  is demoted to a small labelled line below a rule, never given the same visual weight as a cited figure.
 *  Never a sum made from the tiles. */
/** A figure its source states as a floor ("More than 13 crore") reads "13 crore+", not "≈13 crore". */
function atLeast(label: string): boolean {
  return /^(more than|over)\b/i.test(label.trim());
}

export function NationalSummary({ national, basePath = "/eci-files/numbers" }: { national: EciNationalFigure[]; basePath?: string }) {
  const all = national.filter((f) => f.group === "all");
  const primary = all.find((f) => !f.computed) ?? all[0];
  if (!primary) return null;
  const computed = all.filter((f) => f !== primary && f.computed);

  return (
    <section style={{ display: "flex", flexDirection: "column", gap: 14, background: "var(--card)", border: "1px solid var(--rule)", borderRadius: 14, padding: "22px 24px", height: "100%" }}>
      <span className="mono" style={{ fontSize: 11, letterSpacing: "0.06em", textTransform: "uppercase", color: "var(--muted)" }}>Nationwide</span>
      <span className="mono" style={{ fontSize: "clamp(34px,4vw,44px)", fontWeight: 700, color: "var(--eci-ink)", lineHeight: 1 }}>
        {atLeast(primary.label) ? `${countIndian(primary.electors)}+` : `${primary.approx ? "≈" : ""}${countIndian(primary.electors)}`}
      </span>
      <span style={{ fontSize: 16, color: "var(--ink)", lineHeight: 1.4 }}>{primary.label}, {primary.scope}</span>
      <SourceTag f={primary} basePath={basePath} />
      {computed.length > 0 && (
        <>
          <div style={{ height: 1, background: "var(--rule)", margin: "4px 0" }} />
          {computed.map((f) => (
            <p key={f.measure + f.label} style={{ margin: 0, fontSize: 12.5, color: "var(--ink2)", lineHeight: 1.6 }}>
              {f.label}
              {f.as_of ? `, as of ${formatLooseDate(f.as_of)}` : ""}: <b className="mono" style={{ color: "var(--ink)" }}>{f.approx ? "≈" : ""}{countIndian(f.electors)}</b>, {f.scope}.{" "}
              <span
                className="mono"
                style={{
                  display: "inline-flex", alignItems: "center", fontSize: 10.5, fontWeight: 600,
                  letterSpacing: "0.02em", padding: "3px 9px", borderRadius: 999,
                  border: "1px solid var(--border2)", color: "var(--ink2)", background: "var(--sunken)",
                }}
              >
                Our computation
              </span>
            </p>
          ))}
        </>
      )}
    </section>
  );
}

/** The phase-by-phase figures NationalSummary used to show inline, now behind a "Phase-by-phase
 *  figures" disclosure below the tile grid (orchestrator visual-pass fix A). Closed by default. */
export function NationalPhaseBreakdown({ national, basePath = "/eci-files/numbers" }: { national: EciNationalFigure[]; basePath?: string }) {
  const byGroup = (g: EciNationalGroup) => national.filter((f) => f.group === g);
  const phase3 = byGroup("phase_3");
  const phase3Scope = phase3[0]?.scope ?? "";
  const groups = (["phase_1", "phase_2", "phase_3"] as const).filter((g) => byGroup(g).length > 0);
  if (groups.length === 0) return null;

  return (
    <details style={{ marginTop: 22, marginBottom: 22 }}>
      <summary className="mono" style={{ fontSize: 12.5, color: "var(--accent-2)", cursor: "pointer" }}>
        Phase-by-phase figures
      </summary>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 14, marginTop: 14 }}>
        {groups.map((g) => {
          const rows = byGroup(g);
          const title = g === "phase_3" ? `Phase III so far · ${phase3Scope}` : PHASE_TITLE[g];
          return (
            <div key={g} style={{ border: "1px solid var(--rule)", borderRadius: 12, background: "var(--card2)", padding: "14px 16px" }}>
              <div className="serif" style={{ fontSize: 14, fontWeight: 600, marginBottom: 10 }}>{title}</div>
              {rows.map((f) => <FigureRow key={f.measure} f={f} basePath={basePath} />)}
              {g === "phase_3" && (
                <div style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 4 }}>
                  Most Phase III final rolls were not yet published at the last figure in the record.
                </div>
              )}
            </div>
          );
        })}
      </div>
    </details>
  );
}
