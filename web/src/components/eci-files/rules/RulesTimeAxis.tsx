import Link from "next/link";
import type { EciRuleRow } from "@/types/eci-files";
import { LaneChip } from "@/components/eci-files/ui/LaneChip";
import { dateFraction, formatEciDate } from "@/lib/eci-files";

/** Where the axis switches from a compressed pre-2025 stretch to a real linear scale — the record has
 *  39 rule changes from 1993 but most of them land in 2025–2026, so a single linear scale would put
 *  three decades of history in a sliver of pixels. */
const BREAK_DATE = "2025-01-01";
const BREAK_FRAC = 0.16;
/** Two dots closer together than this (as a fraction of the axis width) render as one cluster. */
const CLUSTER_GAP = 0.014;
/** Two year ticks closer than this overlap as text (V5: the compressed pre-2025 stretch crams three
 *  decades into 16% of the axis, so the years around a busy cluster — 2023's Act, say — land close
 *  enough to overlap). Ticks that would collide alternate onto a second row; one that still collides
 *  with both rows' last placed tick is dropped rather than drawn on top of its neighbour. */
const TICK_GAP = 0.032;

interface Dot {
  frac: number;
  rows: EciRuleRow[];
}

interface Tick {
  year: string;
  x: number;
  row: 0 | 1;
}

function layoutTicks(years: string[], xFrac: (date: string) => number): Tick[] {
  const lastX: [number, number] = [-Infinity, -Infinity];
  const out: Tick[] = [];
  for (const year of years) {
    const x = xFrac(`${year}-01-01`);
    let row: 0 | 1 | null = null;
    if (x - lastX[0] >= TICK_GAP) row = 0;
    else if (x - lastX[1] >= TICK_GAP) row = 1;
    if (row === null) continue;
    lastX[row] = x;
    out.push({ year, x, row });
  }
  return out;
}

function clusterDots(rows: EciRuleRow[], xFrac: (date: string) => number): Dot[] {
  const dated = rows.filter((r) => r.entry.date).slice().sort((a, b) => (a.entry.date! < b.entry.date! ? -1 : 1));
  const dots: Dot[] = [];
  for (const row of dated) {
    const frac = xFrac(row.entry.date!);
    const last = dots[dots.length - 1];
    if (last && Math.abs(frac - last.frac) < CLUSTER_GAP) {
      last.rows.push(row);
    } else {
      dots.push({ frac, rows: [row] });
    }
  }
  return dots;
}

/** The single visual answer on `/eci-files/rules`: every rule change on one time axis, coloured by lane,
 *  with a scale break before 2025 (§ above) and a violet ring on any change that has a sourced
 *  before-and-after. Close dates cluster into one dot with a count, rather than an illegible pile-up. */
export function RulesTimeAxis({ rows }: { rows: EciRuleRow[] }) {
  const dated = rows.map((r) => r.entry.date).filter((d): d is string => !!d);
  if (dated.length === 0) return null;
  const minDate = dated.reduce((a, b) => (b < a ? b : a));
  const maxDate = dated.reduce((a, b) => (b > a ? b : a));
  const hasPreBreak = minDate < BREAK_DATE;
  const effectiveMax = maxDate > BREAK_DATE ? maxDate : BREAK_DATE;

  function xFrac(date: string): number {
    if (!hasPreBreak) return dateFraction(date, minDate, maxDate);
    if (date < BREAK_DATE) return dateFraction(date, minDate, BREAK_DATE) * BREAK_FRAC;
    return BREAK_FRAC + dateFraction(date, BREAK_DATE, effectiveMax) * (1 - BREAK_FRAC);
  }

  const dots = clusterDots(rows, xFrac);
  const years = [...new Set(dated.map((d) => d.slice(0, 4)))].sort();
  const lanesPresent = [...new Set(rows.map((r) => r.entry.lane))];

  return (
    <div>
      <div className="eci-legend" style={{ marginBottom: 12 }}>
        {lanesPresent.map((lane) => <LaneChip key={lane} lane={lane} size={11} />)}
        <span className="eci-legend-item">
          <span aria-hidden style={{ width: 12, height: 12, borderRadius: "50%", background: "var(--eci-ink)", boxShadow: "0 0 0 3px color-mix(in srgb, var(--eci-ink) 16%, var(--card)), 0 0 0 4px var(--eci-ink)" }} />
          Has a before/after
        </span>
      </div>
      <div className="eci-rules-axis">
        <div className="eci-rules-axis-scroll">
          <div className="eci-rules-axis-inner">
            {hasPreBreak ? (
              <>
                <span aria-hidden className="eci-rules-axis-line" style={{ left: 0, width: `${BREAK_FRAC * 100}%` }} />
                <span aria-hidden className="eci-rules-axis-break" style={{ left: `${BREAK_FRAC * 100}%` }}>⁄⁄</span>
                <span aria-hidden className="eci-rules-axis-line" style={{ left: `${BREAK_FRAC * 100}%`, right: 0, width: "auto" }} />
              </>
            ) : (
              <span aria-hidden className="eci-rules-axis-line" style={{ left: 0, right: 0, width: "auto" }} />
            )}

            {dots.map((dot, i) => {
              const diffed = dot.rows.some((r) => r.diffs.length > 0);
              const count = dot.rows.length;
              const r = 6 + Math.min(3, count - 1) * 1.6 + (diffed ? 2 : 0);
              const single = count === 1 ? dot.rows[0] : null;
              const lane = single ? single.entry.lane : dot.rows[0].entry.lane;
              const label = single
                ? `${formatEciDate(single.entry.date, single.entry.date_precision)} — ${single.entry.title}${single.diffs.length > 0 ? " (has a before-and-after)" : ""}`
                : `${count} rule changes around ${formatEciDate(dot.rows[0].entry.date, dot.rows[0].entry.date_precision)}${diffed ? ", including one with a before-and-after" : ""}`;
              const href = single
                ? (single.diffs.length === 1 ? `/eci-files/rules/${single.diffs[0].id}` : `#rule-${single.entry.id}`)
                : `#rule-${dot.rows[0].entry.id}`;

              const mark = (
                <span
                  aria-hidden
                  style={{
                    display: "block", width: r * 2, height: r * 2, borderRadius: "50%",
                    background: `var(--eci-lane-${lane})`,
                    boxShadow: diffed ? "0 0 0 3px color-mix(in srgb, var(--eci-ink) 16%, var(--card)), 0 0 0 4px var(--eci-ink)" : undefined,
                  }}
                />
              );

              return (
                <Link
                  key={i}
                  href={href}
                  className="eci-rules-axis-dot"
                  style={{ left: `${dot.frac * 100}%` }}
                  aria-label={label}
                >
                  {mark}
                  {count > 1 && <span aria-hidden className="mono eci-rules-axis-count">{count}</span>}
                </Link>
              );
            })}

            <div className="eci-rules-axis-ticks">
              {layoutTicks(years, xFrac).map((t) => (
                <span key={t.year} className="mono" style={{ left: `${t.x * 100}%`, top: t.row === 1 ? 13 : 0 }}>{t.year}</span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
