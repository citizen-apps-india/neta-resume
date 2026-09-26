import Link from "next/link";
import type { EciPersonSummary } from "@/types/eci-files";
import { ECI_TENURE_AXIS, dateFraction, formatEciDate, membersInOffice, tenureSegments } from "@/lib/eci-files";
import { PersonAvatar } from "@/components/eci-files/PersonAvatar";

const LABEL_COL = 158; // 148px label + 10px row gap (.eci-tchart-row in globals.css)

const ACT_MARKER = { date: "2024-01-02", full: "2023 Act in force" };

function segmentClass(kind: string): string {
  return kind === "cec" ? "eci-tenure-cec" : kind === "ec" ? "eci-tenure-ec" : "eci-tenure-other";
}

function yearTicks(axis: { from: string; to: string }): { x: number; full: string; short: string }[] {
  const fromYear = Number(axis.from.slice(0, 4));
  const toYear = Number(axis.to.slice(0, 4));
  const out: { x: number; full: string; short: string }[] = [];
  for (let y = fromYear; y <= toYear; y++) {
    const iso = `${y}-01-01`;
    if (iso < axis.from) continue;
    out.push({ x: dateFraction(iso, axis.from, axis.to), full: String(y), short: `'${String(y).slice(2)}` });
  }
  return out;
}

function stripTip(from: string, to: string, count: number): string {
  return `${count} member${count === 1 ? "" : "s"}, ${formatEciDate(from, "day")} – ${formatEciDate(to, "day")}`;
}

const SHADE_BY_COUNT: Record<number, number> = { 3: 12, 2: 24, 1: 45, 0: 0 };

/** "Who ran the Commission" (C-After-People.dc.html): hand-built HTML rows on the shared
 *  `ECI_TENURE_AXIS`, one per commissioner — avatar at the row start, EC/CEC shading, one dashed line for
 *  the 2023 Act (the interim court rule that produced no selections gets no marker of its own), and a
 *  small ringed dot at the end of a serving commissioner's bar. Modelled on `DensityStrip`/`LaneTimeline`'s
 *  hybrid of HTML rows and small marks, not a chart library. The "members in office" strip and the table
 *  disclosure stay: they're supporting detail behind the one hero chart, not a second hero. */
export function CommissionTenureChart({
  people, axis = ECI_TENURE_AXIS,
}: {
  people: EciPersonSummary[];
  axis?: { from: string; to: string };
}) {
  const ticks = yearTicks(axis);

  const commissionIntervals = people.flatMap((p) =>
    tenureSegments(p.tenure, axis).filter((s) => s.kind !== "other").map((s) => ({ from: s.from, to: s.to })),
  );
  const strip = membersInOffice(commissionIntervals, axis);
  const markerX = dateFraction(ACT_MARKER.date, axis.from, axis.to) * 100;
  const servingCount = people.filter((p) => p.current).length;

  return (
    <figure style={{ margin: "0 0 28px" }}>
      <div style={{ border: "1px solid var(--rule)", borderRadius: 14, background: "var(--card)", padding: "20px clamp(14px,2vw,24px) 6px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap", gap: 10, marginBottom: 10 }}>
          <h2 style={{ margin: 0, fontSize: 18, fontWeight: 650 }}>Who ran the Commission, 2019–today</h2>
          <span className="mono" style={{ fontSize: 11.5, color: "var(--muted)" }}>
            {people.length} commissioner{people.length === 1 ? "" : "s"} · {servingCount} serving now
          </span>
        </div>

        <div className="eci-legend" style={{ marginBottom: 12 }}>
          <span className="eci-legend-item">
            <span aria-hidden style={{ width: 14, height: 8, borderRadius: 2, background: "color-mix(in srgb, var(--eci-ink) 32%, var(--card))", border: "1px solid var(--eci-ink)" }} />
            Election Commissioner
          </span>
          <span className="eci-legend-item">
            <span aria-hidden style={{ width: 14, height: 8, borderRadius: 2, background: "var(--eci-ink)" }} />
            Chief Election Commissioner
          </span>
          <span className="eci-legend-item">
            <span aria-hidden style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--eci-ink)", boxShadow: "0 0 0 2px var(--card)" }} />
            Serving today
          </span>
          <Link href="/eci-files/selections#regimes" className="eci-legend-item mono" style={{ color: "var(--muted)", textDecoration: "none" }}>
            <span aria-hidden style={{ width: 14, height: 0, borderTop: "1.5px dashed var(--ink)" }} />
            {ACT_MARKER.full} ({formatEciDate(ACT_MARKER.date, "day")})
          </Link>
        </div>

        <div style={{ position: "relative" }}>
          <div className="eci-tchart-markers" aria-hidden style={{ position: "absolute", inset: 0, marginLeft: LABEL_COL, pointerEvents: "none" }}>
            <div style={{ position: "absolute", top: 0, bottom: 0, left: `${markerX}%`, borderLeft: "1.5px dashed var(--ink)" }} />
          </div>

          {people.map((p) => {
            const segments = tenureSegments(p.tenure, axis);
            const rowLabel = `${p.name}, ${
              segments.length > 0
                ? segments.map((s) => `${s.office}, ${s.clippedStart ? "from before 2019" : formatEciDate(s.from, "day")} to ${s.openEnd ? "today" : formatEciDate(s.to, "day")}`).join("; ")
                : "no tenure dates on record"
            }${p.current ? ", serving today" : ""}`;
            return (
              <div key={p.slug} className="eci-tchart-row" style={{ minHeight: 26 }}>
                <span className="eci-tchart-label" style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
                  <PersonAvatar name={p.name} photo={p.photo} size={24} decorative />
                  <span className="serif" title={p.name} style={{ fontSize: 13, fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {p.name}
                  </span>
                </span>
                <div style={{ position: "relative", flex: 1, height: 26 }}>
                  <Link href={`/eci-files/people/${p.slug}`} aria-label={rowLabel} style={{ position: "absolute", inset: 0, display: "block" }}>
                    {segments.map((s, i) => (
                      <span
                        key={i}
                        aria-hidden
                        className={segmentClass(s.kind)}
                        style={{
                          position: "absolute", left: `${s.x0 * 100}%`, width: `${Math.max(0.6, (s.x1 - s.x0) * 100)}%`,
                          top: 9, height: 8, borderRadius: s.openEnd ? "4px 0 0 4px" : 4, display: "block",
                        }}
                      />
                    ))}
                    {segments.some((s) => s.clippedStart) && (
                      <span aria-hidden className="mono" style={{ position: "absolute", left: 0, top: -1, fontSize: 9.5, color: "var(--faint)" }}>◂ from Sep 2017</span>
                    )}
                    {p.current && (
                      <span aria-hidden style={{ position: "absolute", left: "100%", top: "50%", transform: "translate(-50%, -50%)", width: 8, height: 8, borderRadius: "50%", background: "var(--eci-ink)", boxShadow: "0 0 0 2px var(--card)" }} />
                    )}
                  </Link>
                </div>
              </div>
            );
          })}

          <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 6, borderTop: "1px solid var(--rule2)", paddingTop: 6 }}>
            <span className="mono eci-tchart-label" style={{ fontSize: 10, color: "var(--faint)" }}>Members in office</span>
            <div style={{ position: "relative", flex: 1, height: 14, display: "flex" }}>
              {strip.map((run, i) => (
                <div
                  key={i}
                  tabIndex={0}
                  className="eci-strip-run"
                  data-tip={stripTip(run.from, run.to, run.count)}
                  aria-label={stripTip(run.from, run.to, run.count)}
                  style={{
                    position: "absolute", left: `${dateFraction(run.from, axis.from, axis.to) * 100}%`,
                    width: `${Math.max(0.3, (dateFraction(run.to, axis.from, axis.to) - dateFraction(run.from, axis.from, axis.to)) * 100)}%`,
                    height: 14,
                    background: run.count === 0 ? "transparent" : `color-mix(in srgb, var(--eci-ink) ${SHADE_BY_COUNT[run.count] ?? 45}%, var(--card))`,
                  }}
                />
              ))}
            </div>
          </div>

          <div className="eci-tchart-row" style={{ marginTop: 4 }}>
            <span className="eci-tchart-label" aria-hidden />
            <div style={{ position: "relative", flex: 1, height: 18 }} aria-hidden="true">
              {ticks.map((t) => (
                <span key={t.full} className="mono" style={{ position: "absolute", left: `${t.x * 100}%`, fontSize: 10, color: "var(--faint)" }}>
                  <span className="eci-tick-full">{t.full}</span>
                  <span className="eci-tick-short">{t.short}</span>
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      <figcaption style={{ fontSize: 12, color: "var(--muted)", marginTop: 10, maxWidth: "68ch" }}>
        Tenures from each commissioner&apos;s profile entry. The 2023 Act moved selection to a committee of the
        Prime Minister, a minister he nominates and the Leader of Opposition.{" "}
        <Link href="/eci-files/selections" className="mono" style={{ color: "var(--accent-2)", textDecoration: "none" }}>
          How they were chosen →
        </Link>
      </figcaption>

      <details className="eci-more" style={{ marginTop: 10 }}>
        <summary className="mono" style={{ fontSize: 11.5, color: "var(--accent-2)", cursor: "pointer" }}>Show as a table</summary>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5, marginTop: 8 }}>
          <caption style={{ textAlign: "left", fontSize: 11.5, color: "var(--muted)", paddingBottom: 6 }}>
            Every tenure segment on the chart above.
          </caption>
          <thead>
            <tr>
              <th scope="col" style={{ textAlign: "left", padding: "4px 8px", color: "var(--faint)", fontSize: 10.5 }}>Name</th>
              <th scope="col" style={{ textAlign: "left", padding: "4px 8px", color: "var(--faint)", fontSize: 10.5 }}>Office</th>
              <th scope="col" style={{ textAlign: "left", padding: "4px 8px", color: "var(--faint)", fontSize: 10.5 }}>From</th>
              <th scope="col" style={{ textAlign: "left", padding: "4px 8px", color: "var(--faint)", fontSize: 10.5 }}>To</th>
            </tr>
          </thead>
          <tbody>
            {people.flatMap((p) =>
              tenureSegments(p.tenure, axis)
                .filter((s) => s.openEnd || !s.to || s.to >= axis.from)
                .map((s, i) => (
                <tr key={`${p.slug}-${i}`}>
                  <td style={{ padding: "4px 8px", borderTop: "1px solid var(--rule2)" }}>{p.name}</td>
                  <td style={{ padding: "4px 8px", borderTop: "1px solid var(--rule2)" }}>{s.office}</td>
                  <td className="mono" style={{ padding: "4px 8px", borderTop: "1px solid var(--rule2)" }}>{s.clippedStart ? "before 2019" : formatEciDate(s.from, "day")}</td>
                  <td className="mono" style={{ padding: "4px 8px", borderTop: "1px solid var(--rule2)" }}>{s.openEnd ? "present" : formatEciDate(s.to, "day")}</td>
                </tr>
              )),
            )}
          </tbody>
        </table>
      </details>
    </figure>
  );
}
