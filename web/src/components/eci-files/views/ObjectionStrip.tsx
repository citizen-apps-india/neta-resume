import type { EciObjection, EciObjectionPersonCount } from "@/types/eci-files";
import { dateFraction, formatEciDate, formatMonthKey, monthRange } from "@/lib/eci-files";

const AXIS_FROM_MONTH = "2025-11";
const AXIS_TO_MONTH = "2026-09";
const REPORT_DATE = "2026-09-23";

const VIEW_W = 660;
const ROW_H = 44;
const AXIS_H = 24;
const LABEL_W = 92;
const COUNT_W = 34;
const TRACK_X0 = LABEL_W;
const TRACK_X1 = VIEW_W - COUNT_W;

function lastDayOfMonth(key: string): string {
  const [y, m] = key.split("-").map(Number);
  const last = new Date(Date.UTC(y, m, 0)).getUTCDate();
  return `${key}-${String(last).padStart(2, "0")}`;
}

/** Surname only, for the row label — "Sukhbir Singh Sandhu" -> "Sandhu". */
function surname(name: string): string {
  const parts = name.trim().split(/\s+/);
  return parts[parts.length - 1];
}

function trackX(frac: number): number {
  return TRACK_X0 + frac * (TRACK_X1 - TRACK_X0);
}

interface RowMark {
  n: number;
  x: number;
  yOffset: number;
  precision: string;
  joint: boolean;
}

/** The fourteen objections, by commissioner, Nov 2025 to Sep 2026 (PHASE5-SPEC §6.2). Hand-built SVG, no
 *  charting library — a dot per day-precision objection, a dashed ring per month-precision one, and a
 *  connector between rows for a jointly recorded objection. Every mark is a link into the ledger below,
 *  which is the chart's data-table equivalent (screen readers get that in words, not the SVG). */
export function ObjectionStrip({
  objections, byPerson,
}: {
  objections: EciObjection[];
  byPerson: EciObjectionPersonCount[];
}) {
  const months = monthRange(AXIS_FROM_MONTH, AXIS_TO_MONTH);
  const from = `${months[0]}-01`;
  const to = lastDayOfMonth(months[months.length - 1]);

  const rowIndex = new Map(byPerson.map((p, i) => [p.slug, i]));
  const rows: RowMark[][] = byPerson.map(() => []);
  const jointLines: { x: number; y0: number; y1: number }[] = [];

  // Group marks sharing a row + date, so same-day objections in the same row can offset apart.
  const groupKey = (row: number, date: string) => `${row}\u0000${date}`;
  const groups = new Map<string, number[]>();
  for (const o of objections) {
    if (!o.date) continue;
    for (const p of o.by) {
      const row = rowIndex.get(p.slug);
      if (row === undefined) continue;
      const key = groupKey(row, o.date);
      const list = groups.get(key) ?? [];
      list.push(o.n);
      groups.set(key, list);
    }
  }

  for (const o of objections) {
    if (!o.date) continue;
    const x = trackX(dateFraction(o.date, from, to));
    const joint = o.by.length > 1;
    const ys: number[] = [];
    for (const p of o.by) {
      const row = rowIndex.get(p.slug);
      if (row === undefined) continue;
      const group = groups.get(groupKey(row, o.date)) ?? [o.n];
      const k = group.length;
      const i = group.indexOf(o.n);
      const yOffset = k > 1 ? (i - (k - 1) / 2) * 10 : 0;
      rows[row].push({ n: o.n, x, yOffset, precision: o.date_precision, joint });
      ys.push(row * ROW_H + ROW_H / 2 + yOffset);
    }
    if (joint && ys.length > 1) {
      jointLines.push({ x, y0: Math.min(...ys), y1: Math.max(...ys) });
    }
  }

  const height = AXIS_H + ROW_H * byPerson.length;
  const axisY = ROW_H * byPerson.length;

  const ticks = months.map((key, i) => ({
    key,
    x: trackX(dateFraction(`${key}-01`, from, to)),
    label: formatMonthKey(key)[0],
    year: key.endsWith("-01") || i === 0 ? key.slice(0, 4) : null,
  }));

  const dayCount = objections.filter((o) => o.date_precision === "day").length;
  const monthCount = objections.filter((o) => o.date_precision === "month").length;
  const jointCount = objections.filter((o) => o.by.length > 1).length;
  const summary =
    `Objections by commissioner, November 2025 to September 2026: ${byPerson.map((p) => `${p.name.split(" ").pop()} ${p.count}`).join(", ")}, ` +
    `${dayCount} dated to the day, ${monthCount} to the month, ${jointCount} recorded jointly.`;

  return (
    <figure style={{ margin: "0 0 26px" }}>
      <svg
        role="img"
        aria-label={summary}
        viewBox={`0 0 ${VIEW_W} ${height}`}
        width="100%"
        height={height}
        style={{ display: "block", overflow: "visible" }}
      >
        {byPerson.map((p, row) => (
          <g key={p.slug}>
            {row > 0 && <line x1={0} x2={VIEW_W} y1={row * ROW_H} y2={row * ROW_H} stroke="var(--rule2)" strokeWidth={1} />}
            <text x={0} y={row * ROW_H + ROW_H / 2 + 4} fontSize={11} className="mono" fill="var(--ink2)">
              {surname(p.name)}
            </text>
            <text x={VIEW_W} y={row * ROW_H + ROW_H / 2 + 4} fontSize={11} textAnchor="end" className="mono" fill="var(--muted)">
              {p.count}
            </text>
          </g>
        ))}

        {/* report + response marker, 23 Sep 2026 */}
        <g aria-hidden="true">
          <line
            x1={trackX(dateFraction(REPORT_DATE, from, to))} x2={trackX(dateFraction(REPORT_DATE, from, to))}
            y1={0} y2={axisY} stroke="var(--rule)" strokeWidth={1.5} strokeDasharray="3 3"
          />
          <text
            x={trackX(dateFraction(REPORT_DATE, from, to)) + 4} y={11}
            fontSize={10} className="mono" fill="var(--muted)"
          >
            Report and response
          </text>
        </g>

        {jointLines.map((l, i) => (
          <line key={i} x1={l.x} x2={l.x} y1={l.y0} y2={l.y1} stroke="var(--ink2)" strokeWidth={1.5} aria-hidden="true" />
        ))}

        {rows.map((marks, row) =>
          marks.map((m) => {
            const cy = row * ROW_H + ROW_H / 2 + m.yOffset;
            const checked = m.precision === "day";
            const obj = objections.find((o) => o.n === m.n)!;
            const label = `Objection ${m.n}, ${formatEciDate(obj.date, obj.date_precision)}, ${obj.by.map((p) => p.name).join(" and ")}`;
            return (
              <a key={m.n} href={`#objection-${m.n}`} className="eci-obj-mark" aria-label={label}>
                <circle
                  cx={m.x} cy={cy} r={4.5}
                  fill={checked ? "var(--eci-ink)" : "var(--card)"}
                  stroke="var(--eci-ink)"
                  strokeWidth={checked ? 0 : 1.6}
                  strokeDasharray={checked ? undefined : "3 2"}
                />
              </a>
            );
          }),
        )}

        {ticks.map((t) => (
          <g key={t.key}>
            <text x={t.x} y={axisY + 15} fontSize={10} textAnchor="middle" className="mono" fill="var(--faint)">
              {t.label}
            </text>
            {t.year && (
              <text x={t.x} y={axisY + 24} fontSize={9} textAnchor="middle" className="mono" fill="var(--faint)">
                {t.year}
              </text>
            )}
          </g>
        ))}
      </svg>
      <figcaption style={{ marginTop: 6 }}>
        <div className="eci-legend">
          <span className="eci-legend-item"><span style={{ width: 9, height: 9, borderRadius: "50%", background: "var(--eci-ink)", display: "inline-block" }} /> Day known</span>
          <span className="eci-legend-item"><span style={{ width: 9, height: 9, borderRadius: "50%", border: "1.5px dashed var(--eci-ink)", display: "inline-block" }} /> Month known, day not</span>
          <span className="eci-legend-item"><span style={{ width: 12, height: 1.5, background: "var(--ink2)", display: "inline-block" }} /> Joint note</span>
        </div>
        <span style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)" }}>
          Objections by commissioner, November 2025 to September 2026. The ledger below lists the same
          fourteen objections as a table, with the three not itemised in the published reports marked so.
        </span>
      </figcaption>
    </figure>
  );
}
