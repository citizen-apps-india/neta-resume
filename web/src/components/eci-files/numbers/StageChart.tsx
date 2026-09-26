import Link from "next/link";
import { countIndian } from "@/lib/format";
import { formatLooseDate } from "@/lib/eci-files";
import { entryHrefFrom } from "@/lib/eci-numbers";
import { TIER_LABEL } from "@/components/eci-files/CitationList";
import type { EciRegionSummary, EciStageValue } from "@/types/eci-files";

const MINUS = "−";
const ROLL_STAGES: { stage: EciStageValue["stage"]; label: string }[] = [
  { stage: "before", label: "Before the SIR" },
  { stage: "draft", label: "Draft roll" },
  { stage: "final", label: "Final roll" },
];

function stageOf(region: EciRegionSummary, stage: string): EciStageValue | undefined {
  return region.stages.find((s) => s.stage === stage);
}

function beforeToDraftLine(before?: EciStageValue, draft?: EciStageValue): string | null {
  if (!before || !draft) return null;
  const diff = before.electors - draft.electors;
  const pct = ((diff / before.electors) * 100).toFixed(1);
  return `${MINUS} ${countIndian(diff)} not carried into the draft (${pct}%)`;
}

function draftToFinalLine(draft?: EciStageValue, final?: EciStageValue): string | null {
  if (!draft || !final) return null;
  const diff = final.electors - draft.electors;
  const sign = diff >= 0 ? "+" : MINUS;
  return `${sign} ${countIndian(Math.abs(diff))} between draft and final`;
}

function StageBar({ id, stage, max }: { id: string; stage: EciStageValue; max: number }) {
  const widthPct = Math.max(0.6, (stage.electors / max) * 100);
  return (
    <svg viewBox="0 0 100 14" preserveAspectRatio="none" aria-hidden style={{ width: "100%", height: 14, display: "block" }}>
      {stage.computed && (
        <defs>
          <pattern id={id} width={4} height={4} patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
            <rect width={4} height={4} fill="var(--card)" />
            <line x1={0} y1={0} x2={0} y2={4} stroke="var(--eci-ink)" strokeWidth={2} />
          </pattern>
        </defs>
      )}
      <rect x={0} y={0} width={widthPct} height={14} rx={2} fill={stage.computed ? `url(#${id})` : "var(--eci-ink)"} />
    </svg>
  );
}

/** The zero-based, hand-built SVG roll chart (PHASE3-SPEC.md §3.6) — three rows (before/draft/final), a
 *  dashed reference line at the pre-SIR figure, and a delta line between each pair of rows. Returns null
 *  when the region has none of the three roll stages (the entirely-missing regions). */
export function StageChart({ region, basePath }: { region: EciRegionSummary; basePath: string }) {
  const rows = ROLL_STAGES.map((r) => ({ ...r, v: stageOf(region, r.stage) }));
  if (!rows.some((r) => r.v)) return null;

  const max = Math.max(1, ...rows.map((r) => r.v?.electors ?? 0));
  const before = rows[0].v;
  const beforeFrac = before ? (before.electors / max) * 100 : null;

  return (
    <section style={{ marginBottom: 30 }}>
      <h2 className="serif" style={{ fontSize: 17, fontWeight: 600, margin: "0 0 14px" }}>From the pre-SIR roll to the final roll</h2>
      <div style={{ display: "flex", flexDirection: "column" }}>
        {rows.map((row, i) => (
          <div key={row.stage} style={{ marginBottom: 10 }}>
            <div className="eci-stage-row">
              <div>
                <div style={{ fontSize: 13, color: "var(--ink)" }}>{row.label}</div>
                {row.v?.as_of && <div className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>{formatLooseDate(row.v.as_of)}</div>}
              </div>
              {row.v ? (
                <div style={{ position: "relative" }}>
                  <StageBar id={`eci-hatch-${region.slug}-${row.stage}`} stage={row.v} max={max} />
                  {beforeFrac !== null && i > 0 && (
                    <div aria-hidden style={{ position: "absolute", top: -3, bottom: -3, left: `${beforeFrac}%`, borderLeft: "1px dashed var(--border2)" }} />
                  )}
                </div>
              ) : (
                <div style={{ fontSize: 12.5, color: "var(--muted)" }}>— not in the record yet</div>
              )}
              <div style={{ fontSize: 12.5, textAlign: "right", whiteSpace: "nowrap" }}>
                {row.v && (
                  <>
                    <span className="mono">{row.v.approx ? "≈" : ""}{countIndian(row.v.electors)}</span>
                    {row.v.computed && <div className="mono" style={{ fontSize: 10, color: "var(--muted)" }}>computed</div>}
                  </>
                )}
              </div>
            </div>
            {row.v && (
              <div style={{ fontSize: 11, color: "var(--muted)", margin: "3px 0 0 2px" }}>
                Source:{" "}
                <Link href={entryHrefFrom(basePath, row.v.source_entry_id)} style={{ color: "var(--accent-2)", textDecoration: "none" }}>
                  {row.v.source_entry_title}
                </Link>
                {" · "}{TIER_LABEL[row.v.tier] ?? `TIER ${row.v.tier}`}
                {row.v.note && " · See the note below ↓"}
              </div>
            )}
            {i === 0 && beforeToDraftLine(rows[0].v, rows[1].v) && (
              <div className="mono" style={{ fontSize: 11.5, color: "var(--ink2)", margin: "6px 0 0 2px" }}>{beforeToDraftLine(rows[0].v, rows[1].v)}</div>
            )}
            {i === 1 && draftToFinalLine(rows[1].v, rows[2].v) && (
              <div className="mono" style={{ fontSize: 11.5, color: "var(--ink2)", margin: "6px 0 0 2px" }}>{draftToFinalLine(rows[1].v, rows[2].v)}</div>
            )}
          </div>
        ))}
      </div>

      <details style={{ marginTop: 4 }}>
        <summary className="mono" style={{ fontSize: 11.5, color: "var(--accent-2)", cursor: "pointer" }}>Show as a table</summary>
        <div className="nr-xscroll" style={{ marginTop: 8 }}>
          <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 12.5 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--rule)" }}>
                <th scope="col" style={{ textAlign: "left", padding: "6px 8px" }}>Stage</th>
                <th scope="col" style={{ textAlign: "right", padding: "6px 8px" }}>Electors</th>
                <th scope="col" style={{ textAlign: "left", padding: "6px 8px" }}>As of</th>
                <th scope="col" style={{ textAlign: "left", padding: "6px 8px" }}>Source</th>
                <th scope="col" style={{ textAlign: "left", padding: "6px 8px" }}>Tier</th>
                <th scope="col" style={{ textAlign: "left", padding: "6px 8px" }}>Flags</th>
              </tr>
            </thead>
            <tbody>
              {rows.filter((r) => r.v).map((r) => (
                <tr key={r.stage} style={{ borderBottom: "1px solid var(--rule2)" }}>
                  <td style={{ padding: "6px 8px" }}>{r.label}</td>
                  <td className="mono" style={{ textAlign: "right", padding: "6px 8px" }}>{r.v!.electors.toLocaleString("en-IN")}</td>
                  <td className="mono" style={{ padding: "6px 8px" }}>{r.v!.as_of ?? "—"}</td>
                  <td style={{ padding: "6px 8px" }}>
                    <Link href={entryHrefFrom(basePath, r.v!.source_entry_id)} style={{ color: "var(--accent-2)" }}>{r.v!.source_entry_title}</Link>
                  </td>
                  <td style={{ padding: "6px 8px" }}>{TIER_LABEL[r.v!.tier] ?? `TIER ${r.v!.tier}`}</td>
                  <td style={{ padding: "6px 8px" }}>{[r.v!.computed && "computed", r.v!.approx && "rounded"].filter(Boolean).join(", ") || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>

      <p style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 10, maxWidth: "68ch" }}>
        Every bar starts at zero. Differences are simple subtraction of the cited figures. A computed
        stage&apos;s method is in its note.
      </p>
    </section>
  );
}
