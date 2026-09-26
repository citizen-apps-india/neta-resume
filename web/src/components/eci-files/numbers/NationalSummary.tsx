import Link from "next/link";
import { countIndian } from "@/lib/format";
import { StatusChip } from "@/components/eci-files/StatusChip";
import { entryHrefFrom } from "@/lib/eci-numbers";
import type { EciNationalFigure, EciNationalGroup } from "@/types/eci-files";

const PHASE_TITLE: Partial<Record<EciNationalGroup, string>> = {
  phase_1: "Phase I · Bihar",
  phase_2: "Phase II · 12 States/UTs",
};

function FigureRow({ f, basePath, big }: { f: EciNationalFigure; basePath: string; big?: boolean }) {
  return (
    <div style={{ marginBottom: big ? 6 : 10 }}>
      <div className="mono" style={{ fontSize: big ? "clamp(26px,5vw,34px)" : 15, fontWeight: 700, color: "var(--eci-ink)", lineHeight: 1.1 }}>
        {f.approx ? "≈" : ""}{countIndian(f.electors)}
      </div>
      <div style={{ fontSize: big ? 13.5 : 12, color: "var(--ink2)", margin: "2px 0" }}>{f.label}</div>
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        {f.as_of && <span className="mono" style={{ fontSize: 10.5, color: "var(--faint)" }}>{f.as_of}</span>}
        <Link href={entryHrefFrom(basePath, f.source_entry_id)} className="mono" style={{ fontSize: 10.5, color: "var(--accent-2)", textDecoration: "none" }}>
          Source: {f.source_entry_title}
        </Link>
        <StatusChip status={f.source_status} />
      </div>
      {f.note && <div style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 4, maxWidth: "68ch" }}>{f.note}</div>}
    </div>
  );
}

/** The record's own national totals — never sums made from the tiles, except the one row marked
 *  "computed" (PHASE3-SPEC.md §1.3/§3.7). */
export function NationalSummary({ national, basePath = "/eci-files/numbers" }: { national: EciNationalFigure[]; basePath?: string }) {
  const all = national.filter((f) => f.group === "all");
  const byGroup = (g: EciNationalGroup) => national.filter((f) => f.group === g);
  const phase3 = byGroup("phase_3");
  const phase3Scope = phase3[0]?.scope ?? "";

  if (national.length === 0) return null;

  return (
    <section style={{ marginBottom: 28 }}>
      {all.map((f, i) => <FigureRow key={f.label} f={f} basePath={basePath} big={i === 0} />)}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 14, marginTop: 16 }}>
        {(["phase_1", "phase_2", "phase_3"] as const).map((g) => {
          const rows = byGroup(g);
          if (rows.length === 0) return null;
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

      <p style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 14, maxWidth: "70ch" }}>
        These totals are the ones the record itself carries — an ECI bulletin, or a newspaper&apos;s own
        tally — not sums we made from the tiles, except the one marked &ldquo;our sum&rdquo;. Different
        tallies use different dates and bases, so they don&apos;t add up exactly.
      </p>
    </section>
  );
}
