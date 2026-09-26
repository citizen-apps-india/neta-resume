import Link from "next/link";
import type { EciPersonSummary, EciSelections } from "@/types/eci-files";
import { ECI_TENURE_AXIS, dateFraction, formatEciDate, membersInOffice, tenureSegments } from "@/lib/eci-files";

const LABEL_COL = 158; // 148px label + 10px row gap (.eci-tchart-row in globals.css)

const MARKERS = [
  { date: "2023-03-02", style: "dashed" as const, full: "Court's interim rule", short: "Court rule" },
  { date: "2024-01-02", style: "solid" as const, full: "2023 Act in force", short: "2023 Act" },
];

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

/** "Who ran the Commission" (PHASE4-SPEC.md §1.2): hand-built HTML/SVG rows on the shared
 *  `ECI_TENURE_AXIS`, one per commissioner, plus a "members in office" strip and the two rule-change
 *  markers. Modelled on `DensityStrip`/`LaneTimeline`'s hybrid of HTML rows and small SVG marks, not a
 *  chart library. Markers and diamonds line up under the bar column via a fixed `LABEL_COL` offset,
 *  which only holds at ≥640px — the marker overlay hides on phones, where rows stack (name above bar). */
export function CommissionTenureChart({
  people, selectionsData, axis = ECI_TENURE_AXIS,
}: {
  people: EciPersonSummary[];
  selectionsData: EciSelections | null;
  axis?: { from: string; to: string };
}) {
  const regimeLabel = new Map(selectionsData?.regimes.map((r) => [r.key, r.label]) ?? []);
  const ticks = yearTicks(axis);

  const commissionIntervals = people.flatMap((p) =>
    tenureSegments(p.tenure, axis).filter((s) => s.kind !== "other").map((s) => ({ from: s.from, to: s.to })),
  );
  const strip = membersInOffice(commissionIntervals, axis);

  const diamondsBySlug = new Map<string, { x: number; selection: EciSelections["selections"][number] }[]>();
  for (const sel of selectionsData?.selections ?? []) {
    const x = dateFraction(sel.date, axis.from, axis.to);
    for (const a of sel.appointed) {
      const list = diamondsBySlug.get(a.person_slug) ?? [];
      list.push({ x, selection: sel });
      diamondsBySlug.set(a.person_slug, list);
    }
  }

  return (
    <figure style={{ margin: "0 0 28px" }}>
      <div className="eci-legend" style={{ marginBottom: 12 }}>
        <span className="eci-legend-item">
          <span aria-hidden style={{ width: 14, height: 8, borderRadius: 2, background: "color-mix(in srgb, var(--eci-ink) 32%, var(--card))", border: "1px solid var(--eci-ink)" }} />
          Election Commissioner
        </span>
        <span className="eci-legend-item">
          <span aria-hidden style={{ width: 14, height: 8, borderRadius: 2, background: "var(--eci-ink)" }} />
          Chief Election Commissioner
        </span>
        <span className="eci-legend-item"><span aria-hidden style={{ fontSize: 13, color: "var(--eci-ink)" }}>◆</span> Selection</span>
        <span className="eci-legend-item"><span aria-hidden style={{ fontSize: 13, color: "var(--eci-ink)" }}>◇</span> Selection with a recorded dissent</span>
      </div>

      <div style={{ border: "1px solid var(--rule)", borderRadius: 12, background: "var(--card)", padding: "10px clamp(10px,2vw,18px) 4px" }}>
        {/* marker labels */}
        <div style={{ position: "relative", height: 16, marginLeft: LABEL_COL }}>
          {MARKERS.map((m) => (
            <Link
              key={m.date}
              href="/eci-files/selections#regimes"
              className="mono"
              style={{ position: "absolute", left: `${dateFraction(m.date, axis.from, axis.to) * 100}%`, transform: "translateX(-50%)", fontSize: 10, color: "var(--muted)", textDecoration: "none", whiteSpace: "nowrap" }}
            >
              <span className="eci-marker-full">{m.full}</span>
              <span className="eci-marker-short">{m.short}</span>
            </Link>
          ))}
        </div>

        <div style={{ position: "relative" }}>
          <div className="eci-tchart-markers" aria-hidden style={{ position: "absolute", inset: 0, marginLeft: LABEL_COL, pointerEvents: "none" }}>
            {MARKERS.map((m) => (
              <div
                key={m.date}
                style={{
                  position: "absolute", top: 0, bottom: 0, left: `${dateFraction(m.date, axis.from, axis.to) * 100}%`,
                  borderLeft: m.style === "dashed" ? "1.5px dashed var(--faint)" : "1.5px solid var(--eci-ink)",
                }}
              />
            ))}
          </div>

          {people.map((p) => {
            const segments = tenureSegments(p.tenure, axis);
            const diamonds = diamondsBySlug.get(p.slug) ?? [];
            const rowLabel = `${p.name}, ${
              segments.length > 0
                ? segments.map((s) => `${s.office}, ${s.clippedStart ? "from before 2019" : formatEciDate(s.from, "day")} to ${s.openEnd ? "today" : formatEciDate(s.to, "day")}`).join("; ")
                : "no tenure dates on record"
            }`;
            return (
              <div key={p.slug} className="eci-tchart-row" style={{ minHeight: 26 }}>
                <span className="eci-tchart-label serif" style={{ fontSize: 13, fontWeight: 600 }}>{p.name}</span>
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
                  </Link>
                  {diamonds.map(({ x, selection }, i) => {
                    const dissented = selection.dissent.length > 0;
                    const label = `Selected ${formatEciDate(selection.date, "day")} under ${regimeLabel.get(selection.regime) ?? selection.regime}${
                      dissented ? `, ${selection.dissent.length === 1 ? "one dissent" : `${selection.dissent.length} dissents`} recorded` : ""
                    }`;
                    return (
                      <a
                        key={i}
                        href={`/eci-files/selections#${selection.id}`}
                        aria-label={label}
                        className="eci-diamond-link"
                        style={{ position: "absolute", left: `${x * 100}%`, top: "50%", transform: "translate(-50%, -50%)", zIndex: 2, lineHeight: 0 }}
                      >
                        <svg width={14} height={14} viewBox="0 0 14 14">
                          <rect
                            x={2} y={2} width={10} height={10} transform="rotate(45 7 7)"
                            fill={dissented ? "var(--card)" : "var(--eci-ink)"}
                            stroke="var(--eci-ink)" strokeWidth={dissented ? 2 : 0}
                          />
                        </svg>
                      </a>
                    );
                  })}
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
              tenureSegments(p.tenure, axis).map((s, i) => (
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
