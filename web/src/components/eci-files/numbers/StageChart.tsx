import Link from "next/link";
import { countIndian } from "@/lib/format";
import { eciEntryHref, formatLooseDate } from "@/lib/eci-files";
import { countIndianRough } from "@/lib/eci-numbers";
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

/** launch fixdata B2: where the draft entry reports the left-off count directly (a `left_off` stage),
 *  use it instead of subtracting `before` and `draft` — the two roll totals are each independently
 *  rounded in some states and don't subtract to the reported count. Falling back to the subtraction,
 *  an approximate result is shown at rougher precision, not to two decimal places it doesn't have. */
function beforeToDraftLine(region: EciRegionSummary, before?: EciStageValue, draft?: EciStageValue): string | null {
  const leftOff = stageOf(region, "left_off");
  if (leftOff && before) {
    const pct = ((leftOff.electors / before.electors) * 100).toFixed(1);
    const count = leftOff.approx ? countIndianRough(leftOff.electors) : countIndian(leftOff.electors);
    return `${MINUS} ${count} not carried into the draft (${pct}%)`;
  }
  if (!before || !draft) return null;
  const diff = before.electors - draft.electors;
  const pct = ((diff / before.electors) * 100).toFixed(1);
  const count = before.approx || draft.approx ? countIndianRough(diff) : countIndian(diff);
  return `${MINUS} ${count} not carried into the draft (${pct}%)`;
}

/** launch fixdata S4: West Bengal's "between draft and final" figure also breaks down into the two
 *  named components (`under_adjudication`, `form7_deletions`) when the record has them, so the
 *  60.07 lakh held under adjudication are not read as ordinary deletions. */
function draftToFinalLines(region: EciRegionSummary, draft?: EciStageValue, final?: EciStageValue): string[] | null {
  if (!draft || !final) return null;
  const diff = final.electors - draft.electors;
  const sign = diff >= 0 ? "+" : MINUS;
  const lines = [`${sign} ${countIndian(Math.abs(diff))} between draft and final`];
  const underAdjudication = stageOf(region, "under_adjudication");
  const form7 = stageOf(region, "form7_deletions");
  if (underAdjudication) {
    lines.push(`${MINUS} ${countIndian(underAdjudication.electors)} held under adjudication`);
  }
  if (form7) {
    lines.push(`${MINUS} ${countIndian(form7.electors)} Form 7 deletions`);
  }
  return lines;
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

/** A challenge is not a further cut to the roll — drawn hollow and dashed, never filled like a real drop
 *  (docs/eci-files/designs/B-After-State.dc.html: "appeals as a dashed 'challenge, not a cut' bar"). */
function AppealsBar({ stage, max }: { stage: EciStageValue; max: number }) {
  const widthPct = Math.max(1.2, (stage.electors / max) * 100);
  return (
    <svg viewBox="0 0 100 14" preserveAspectRatio="none" aria-hidden style={{ width: "100%", height: 14, display: "block" }}>
      <rect x={1} y={1} width={Math.max(0, widthPct - 2)} height={12} rx={2} fill="none" stroke="var(--eci-ink)" strokeWidth={2} strokeDasharray="4 3" />
    </svg>
  );
}

/** The zero-based, hand-built SVG roll chart (PHASE3-SPEC.md §3.6) — three rows (before/draft/final), a
 *  dashed reference line at the pre-SIR figure, and a delta line between each pair of rows. Returns null
 *  when the region has none of the three roll stages (the entirely-missing regions). */
export function StageChart({ region, basePath }: { region: EciRegionSummary; basePath: string }) {
  const rows = ROLL_STAGES.map((r) => ({ ...r, v: stageOf(region, r.stage) }));
  if (!rows.some((r) => r.v)) return null;

  const appeals = stageOf(region, "appeals_filed");
  const final = rows[2].v;
  const appealsPct = appeals && final ? ((appeals.electors / final.electors) * 100).toFixed(1) : null;

  const max = Math.max(1, ...rows.map((r) => r.v?.electors ?? 0), appeals?.electors ?? 0);
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
                <Link href={eciEntryHref(row.v.source_entry_id, {}, basePath)} style={{ color: "var(--accent-2)", textDecoration: "none" }}>
                  {row.v.source_entry_title}
                </Link>
                {" · "}{TIER_LABEL[row.v.tier] ?? `TIER ${row.v.tier}`}
                {row.v.note && " · See the note below ↓"}
              </div>
            )}
            {i === 0 && beforeToDraftLine(region, rows[0].v, rows[1].v) && (
              <div className="mono" style={{ fontSize: 11.5, color: "var(--ink2)", margin: "6px 0 0 2px" }}>{beforeToDraftLine(region, rows[0].v, rows[1].v)}</div>
            )}
            {i === 1 && draftToFinalLines(region, rows[1].v, rows[2].v)?.map((line, idx) => (
              <div key={idx} className="mono" style={{ fontSize: 11.5, color: "var(--ink2)", margin: "6px 0 0 2px" }}>{line}</div>
            ))}
          </div>
        ))}
        {appeals && (
          <div style={{ marginTop: 4 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "0 0 6px 10px" }}>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                <path d="M7 2V12M7 12L3.5 8.5M7 12L10.5 8.5" stroke="var(--border2)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span className="mono" style={{ fontSize: 12, color: "var(--muted)" }}>not a further cut — a challenge to the roll above</span>
            </div>
            <div className="eci-stage-row">
              <div>
                <div style={{ fontSize: 13, color: "var(--ink)" }}>Appeals against the adjudication orders</div>
                {appeals.as_of && <div className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>{formatLooseDate(appeals.as_of)}</div>}
              </div>
              <AppealsBar stage={appeals} max={max} />
              <div style={{ fontSize: 12.5, textAlign: "right", whiteSpace: "nowrap" }}>
                <span className="mono">{appeals.approx ? "≈" : ""}{countIndian(appeals.electors)}</span>
                {appealsPct && <div className="mono" style={{ fontSize: 10, color: "var(--muted)" }}>{appealsPct}% of final</div>}
              </div>
            </div>
            <div style={{ fontSize: 11, color: "var(--muted)", margin: "3px 0 0 2px" }}>
              Source:{" "}
              <Link href={eciEntryHref(appeals.source_entry_id, {}, basePath)} style={{ color: "var(--accent-2)", textDecoration: "none" }}>
                {appeals.source_entry_title}
              </Link>
              {" · "}{TIER_LABEL[appeals.tier] ?? `TIER ${appeals.tier}`}
            </div>
          </div>
        )}
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
              {[...rows, ...(appeals ? [{ stage: "appeals_filed" as const, label: "Appeals filed (challenge, not a cut)", v: appeals }] : [])]
                .filter((r) => r.v)
                .map((r) => (
                  <tr key={r.stage} style={{ borderBottom: "1px solid var(--rule2)" }}>
                    <td style={{ padding: "6px 8px" }}>{r.label}</td>
                    <td className="mono" style={{ textAlign: "right", padding: "6px 8px" }}>{r.v!.electors.toLocaleString("en-IN")}</td>
                    <td className="mono" style={{ padding: "6px 8px" }}>{r.v!.as_of ?? "—"}</td>
                    <td style={{ padding: "6px 8px" }}>
                      <Link href={eciEntryHref(r.v!.source_entry_id, {}, basePath)} style={{ color: "var(--accent-2)" }}>{r.v!.source_entry_title}</Link>
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
