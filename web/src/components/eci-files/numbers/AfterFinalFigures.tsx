import Link from "next/link";
import { countIndian } from "@/lib/format";
import { eciEntryHref, formatLooseDate } from "@/lib/eci-files";
import { TIER_LABEL } from "@/components/eci-files/CitationList";
import type { EciRegionSummary, EciStageValue } from "@/types/eci-files";

const AFTER_STAGES: { stage: EciStageValue["stage"]; label: string }[] = [
  { stage: "appeals_pending", label: "Appeals still pending" },
  { stage: "restored", label: "Restored after appeal" },
];

/** Counts of applications, not roll sizes — no bar, plain figure rows (PHASE3-SPEC.md §3.6).
 *  `appeals_filed` moved into {@link StageChart}'s waterfall hero as the dashed "challenge, not a cut"
 *  bar (docs/eci-files/designs/B-After-State.dc.html); this section carries only what's left: appeals
 *  still pending and electors restored after appeal. Shown only when the region has one of the two;
 *  today that's West Bengal alone (PHASES-3-5-DECISIONS.md). */
export function AfterFinalFigures({ region, basePath }: { region: EciRegionSummary; basePath: string }) {
  const rows = AFTER_STAGES.map((a) => ({ ...a, v: region.stages.find((s) => s.stage === a.stage) })).filter((r) => r.v);
  if (rows.length === 0) return null;

  return (
    <section style={{ marginBottom: 30 }}>
      <h2 className="serif" style={{ fontSize: 17, fontWeight: 600, margin: "0 0 12px" }}>After the final roll</h2>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {rows.map(({ stage, label, v }) => {
          const stg = v!;
          return (
            <div key={stage} style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8, borderBottom: "1px solid var(--rule2)", paddingBottom: 8 }}>
              <div>
                <div style={{ fontSize: 13, color: "var(--ink)" }}>{label}</div>
                <div style={{ fontSize: 11, color: "var(--muted)" }}>
                  Source:{" "}
                  <Link href={eciEntryHref(stg.source_entry_id, {}, basePath)} style={{ color: "var(--accent-2)", textDecoration: "none" }}>
                    {stg.source_entry_title}
                  </Link>
                  {" · "}{TIER_LABEL[stg.tier] ?? `TIER ${stg.tier}`}
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div className="mono">{stg.approx ? "≈" : ""}{countIndian(stg.electors)}</div>
                <div className="mono" style={{ fontSize: 10.5, color: "var(--faint)" }}>{formatLooseDate(stg.as_of)}</div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
