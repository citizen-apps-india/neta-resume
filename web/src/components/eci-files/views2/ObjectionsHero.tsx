import Link from "next/link";
import type { EciEntryCard, EciObjection, EciObjectionPersonCount } from "@/types/eci-files";
import { dateFraction, eciEntryHref, formatEciDate, formatMonthKey, monthRange } from "@/lib/eci-files";
import { PersonAvatar } from "@/components/eci-files/views/PersonAvatar";

const AXIS_FROM_MONTH = "2025-11";
const AXIS_TO_MONTH = "2026-09";

const TRACK_W = 640;
const RIGHT_PAD = 64;
const DATE_SPAN = TRACK_W - RIGHT_PAD;
const ROW_H = 54;
const AXIS_H = 28;

function lastDayOfMonth(key: string): string {
  const [y, m] = key.split("-").map(Number);
  const last = new Date(Date.UTC(y, m, 0)).getUTCDate();
  return `${key}-${String(last).padStart(2, "0")}`;
}

interface Mark {
  n: number;
  x: number;
  yOffset: number;
  day: boolean;
}

/** Surname only — the label column already carries the full name, so the "Both" row and marker labels
 *  stay short. */
function surname(name: string): string {
  const parts = name.trim().split(/\s+/);
  return parts[parts.length - 1];
}

/** The objections page's one visual answer: a three-lane time axis (a named commissioner's lane above and
 *  below a shared "Both" lane for jointly recorded objections) running Nov 2025–Sep 2026, plus the
 *  Commission's response as an attributed quote. Faithful to
 *  `docs/eci-files/designs/D-After-Objections.dc.html`. A hand-drawn SVG for the marks (no charting
 *  library, same call as the pre-existing `ObjectionStrip`); the ledger below is this chart's data-table
 *  equivalent, so nothing here is the only place a fact lives. */
export function ObjectionsHero({
  objections, byPerson, missing, reportedTotal, response, basePath,
}: {
  objections: EciObjection[];
  byPerson: EciObjectionPersonCount[];
  missing: number;
  reportedTotal: number;
  response: EciEntryCard | null;
  basePath: string;
}) {
  const months = monthRange(AXIS_FROM_MONTH, AXIS_TO_MONTH);
  const from = `${months[0]}-01`;
  const to = lastDayOfMonth(months[months.length - 1]);
  const trackX = (frac: number) => frac * DATE_SPAN;

  const hasBoth = byPerson.length === 2;
  const laneCount = hasBoth ? 3 : Math.max(1, byPerson.length);
  const bothRow = hasBoth ? 1 : -1;
  const laneOf = (slug: string): number => {
    if (!hasBoth) return byPerson.findIndex((p) => p.slug === slug);
    return byPerson[0]?.slug === slug ? 0 : 2;
  };
  const rowCenter = (row: number) => row * ROW_H + ROW_H / 2;

  const rowOf = (o: EciObjection): number => (o.by.length > 1 ? bothRow : laneOf(o.by[0]?.slug ?? ""));

  const groups = new Map<string, number[]>();
  for (const o of objections) {
    if (!o.date) continue;
    const row = rowOf(o);
    if (row < 0) continue;
    const key = `${row}\u0000${o.date}`;
    const list = groups.get(key) ?? [];
    list.push(o.n);
    groups.set(key, list);
  }

  const rows: Mark[][] = Array.from({ length: laneCount }, () => []);
  for (const o of objections) {
    if (!o.date) continue;
    const row = rowOf(o);
    if (row < 0) continue;
    const x = trackX(dateFraction(o.date, from, to));
    const group = groups.get(`${row}\u0000${o.date}`) ?? [o.n];
    const k = group.length;
    const i = group.indexOf(o.n);
    const yOffset = k > 1 ? (i - (k - 1) / 2) * 11 : 0;
    rows[row].push({ n: o.n, x, yOffset, day: o.date_precision === "day" });
  }

  const jointCount = objections.filter((o) => o.date && o.by.length > 1).length;
  const axisY = ROW_H * laneCount;
  const height = axisY + AXIS_H;

  const ticks = months.map((key, i) => ({
    key,
    x: trackX(dateFraction(`${key}-01`, from, to)),
    label: formatMonthKey(key).slice(0, 3),
    year: i === 0 || key.endsWith("-01") ? key.slice(0, 4) : null,
  }));

  const missingX = Array.from({ length: missing }, (_, i) => DATE_SPAN + 22 + i * 15);
  const missingRow = hasBoth ? bothRow : laneCount - 1;

  return (
    <div className="eci2-hero-grid">
      <div className="eci2-card">
        <div className="mono eci2-eyebrow" style={{ marginBottom: 14 }}>
          {reportedTotal} objections · Nov 2025 – Sep 2026
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "168px minmax(0,1fr)", gap: 12, alignItems: "start" }}>
          <div style={{ display: "flex", flexDirection: "column" }}>
            {byPerson.map((p, i) => {
              const row = hasBoth ? (i === 0 ? 0 : 2) : i;
              return (
                <div key={p.slug} style={{ height: ROW_H, display: "flex", alignItems: "center", gap: 8, order: row }}>
                  <PersonAvatar name={p.name} photo={p.photo} size={30} decorative />
                  <div style={{ display: "flex", flexDirection: "column", gap: 1, minWidth: 0 }}>
                    <strong style={{ fontSize: 12.5, lineHeight: 1.2 }}>{p.name}</strong>
                    <span className="mono" style={{ fontSize: 10.5, color: "var(--muted)" }}>
                      {p.count} objections{p.joint > 0 ? ` · ${p.joint} joint` : ""}
                    </span>
                  </div>
                </div>
              );
            })}
            {hasBoth && (
              <div style={{ height: ROW_H, display: "flex", alignItems: "center", order: 1 }}>
                <span className="mono" style={{ fontSize: 10.5, color: "var(--muted)" }}>
                  Both{jointCount > 0 ? ` · ${jointCount} joint note${jointCount === 1 ? "" : "s"}` : ""}
                </span>
              </div>
            )}
          </div>

          <div style={{ overflow: "visible" }}>
            <svg
              role="img"
              aria-label={`Objections by commissioner, November 2025 to September 2026: ${byPerson
                .map((p) => `${surname(p.name)} ${p.count}`)
                .join(", ")}, ${objections.filter((o) => o.date_precision === "day").length} dated to the day, ${
                objections.filter((o) => o.date_precision === "month").length
              } to the month, ${jointCount} recorded jointly, ${missing} not itemised in the published reports.`}
              viewBox={`0 0 ${TRACK_W} ${height}`}
              width="100%"
              height={height}
              style={{ display: "block", overflow: "visible" }}
            >
              {Array.from({ length: laneCount - 1 }).map((_, row) => (
                <line key={row} x1={0} x2={TRACK_W} y1={(row + 1) * ROW_H} y2={(row + 1) * ROW_H} stroke="var(--rule2)" strokeWidth={1} />
              ))}

              <line x1={0} x2={DATE_SPAN} y1={axisY} y2={axisY} stroke="var(--border)" strokeWidth={1} />

              {rows.map((marks, row) =>
                marks.map((m) => {
                  const obj = objections.find((o) => o.n === m.n)!;
                  const joint = obj.by.length > 1;
                  const cy = rowCenter(row) + m.yOffset;
                  const label = `Objection ${m.n}, ${formatEciDate(obj.date, obj.date_precision)}, ${obj.by
                    .map((p) => p.name)
                    .join(" and ")}`;
                  const colour = joint ? "var(--eci-seq-5)" : row === 0 ? "var(--eci-ink)" : "var(--eci-seq-3)";
                  return (
                    <a key={m.n} href={`#eci2-objection-${m.n}`} className="eci-obj-mark" aria-label={label}>
                      {joint ? (
                        <rect
                          x={m.x - 5} y={cy - 5} width={10} height={10} rx={1.5}
                          transform={`rotate(45 ${m.x} ${cy})`}
                          fill={colour} stroke="var(--card)" strokeWidth={1.5}
                        />
                      ) : (
                        <circle
                          cx={m.x} cy={cy} r={5}
                          fill={m.day ? colour : "var(--card)"}
                          stroke={colour}
                          strokeWidth={m.day ? 0 : 2}
                        />
                      )}
                    </a>
                  );
                }),
              )}

              {missingX.map((x, i) => (
                <circle
                  key={i} cx={x} cy={rowCenter(missingRow)} r={5}
                  fill="none" stroke="var(--faint)" strokeWidth={1.5} strokeDasharray="3 2" aria-hidden="true"
                />
              ))}

              {ticks.map((t) => (
                <g key={t.key}>
                  <line x1={t.x} x2={t.x} y1={axisY} y2={axisY + 5} stroke="var(--border)" strokeWidth={1} aria-hidden="true" />
                  <text x={t.x} y={axisY + 17} fontSize={10} textAnchor="middle" className="mono" fill="var(--muted)">
                    {t.label}
                  </text>
                  {t.year && (
                    <text x={t.x} y={axisY + 27} fontSize={9} textAnchor="middle" className="mono" fill="var(--faint)">
                      {t.year}
                    </text>
                  )}
                </g>
              ))}
            </svg>
          </div>
        </div>

        <div className="eci-legend" style={{ marginTop: 12 }}>
          <span className="eci-legend-item">
            <span aria-hidden style={{ width: 10, height: 10, borderRadius: "50%", background: "var(--eci-ink)", display: "inline-block" }} />
            Date known
          </span>
          <span className="eci-legend-item">
            <span aria-hidden style={{ width: 10, height: 10, borderRadius: "50%", border: "2px solid var(--eci-ink)", display: "inline-block" }} />
            Month known, day not
          </span>
          <span className="eci-legend-item">
            <span aria-hidden style={{ width: 9, height: 9, background: "var(--eci-seq-5)", display: "inline-block", transform: "rotate(45deg)" }} />
            Both commissioners
          </span>
          <span className="eci-legend-item">
            <span aria-hidden style={{ width: 10, height: 10, borderRadius: "50%", border: "1.5px dashed var(--faint)", display: "inline-block" }} />
            Not itemised
          </span>
        </div>
        <p style={{ fontSize: 13, lineHeight: 1.55, color: "var(--ink2)", margin: "10px 0 0" }}>
          The Indian Express&rsquo;s report says <strong>{missing} more objections are reported but not itemised</strong> in
          its published account &mdash; shown as the dashed circles above, past September 2026.
        </p>
      </div>

      <div className="eci2-card eci2-response-card">
        <span className="mono eci2-eyebrow">The Commission&rsquo;s response</span>
        {response ? (
          <>
            <p className="eci2-quote">&ldquo;{response.title}&rdquo;</p>
            <p style={{ fontSize: 13.5, lineHeight: 1.55, color: "var(--ink2)", margin: 0 }}>{response.summary}</p>
            <div className="eci2-response-foot">
              <span className="mono" style={{ fontSize: 11.5, color: "var(--muted)" }}>
                {response.attributed_to ?? "Election Commission of India"} · {formatEciDate(response.date, response.date_precision)}
              </span>
              <Link href={eciEntryHref(response.id, {}, basePath)} className="mono" style={{ fontSize: 13.5, color: "var(--accent-2)", textDecoration: "none" }}>
                Read the press note →
              </Link>
            </div>
          </>
        ) : (
          <p style={{ fontSize: 13, color: "var(--muted)" }}>No response is on record.</p>
        )}
      </div>
    </div>
  );
}
