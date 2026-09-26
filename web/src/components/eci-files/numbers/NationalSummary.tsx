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

/** One headline tile: value, short label and source link — no note, no big/small split, so a row of
 *  these stays a single compact band instead of the old text wall (orchestrator visual-pass fix A). */
function HeadlineTile({ f, basePath }: { f: EciNationalFigure; basePath: string }) {
  return (
    <div style={{ minWidth: 200, flex: "1 1 200px" }}>
      <div className="mono" style={{ fontSize: "clamp(19px,2.6vw,23px)", fontWeight: 700, color: "var(--eci-ink)", lineHeight: 1.15 }}>
        {f.approx ? "≈" : ""}{countIndian(f.electors)}
      </div>
      <div style={{ fontSize: 12, color: "var(--ink2)", margin: "2px 0 5px" }}>{f.label}</div>
      <SourceTag f={f} basePath={basePath} />
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

/** The record's own national totals, compact: one row of headline figures (the "all" group — never a
 *  sum made from the tiles, except the one row marked "computed"). The phase-by-phase breakdown lives
 *  in {@link NationalPhaseBreakdown}, collapsed behind a disclosure below the tile grid, so this section
 *  never pushes the grid below the fold (PHASE3-SPEC.md §1.3/§3.7). */
export function NationalSummary({ national, basePath = "/eci-files/numbers" }: { national: EciNationalFigure[]; basePath?: string }) {
  const all = national.filter((f) => f.group === "all");
  if (all.length === 0) return null;

  return (
    <section style={{ marginBottom: 20 }}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "14px 28px" }}>
        {all.map((f) => <HeadlineTile key={f.label} f={f} basePath={basePath} />)}
      </div>
      <p style={{ fontSize: 11, color: "var(--muted)", marginTop: 10, maxWidth: "70ch" }}>
        These totals are the ones the record itself carries — an ECI bulletin, or a newspaper&apos;s own
        tally — not sums we made from the tiles, except the one marked &ldquo;our sum&rdquo;.
      </p>
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
