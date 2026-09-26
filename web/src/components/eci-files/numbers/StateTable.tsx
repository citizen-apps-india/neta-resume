import Link from "next/link";
import { countIndian } from "@/lib/format";
import { formatLooseDate } from "@/lib/eci-files";
import { countIndianRough, formatPercent, romanPhase, type EciMetricDef } from "@/lib/eci-numbers";
import type { EciRegionSummary } from "@/types/eci-files";

function StageCell({ region, stage }: { region: EciRegionSummary; stage: string }) {
  const s = region.stages.find((x) => x.stage === stage);
  if (!s) {
    return <td className="eci-col-stage mono" style={{ padding: "6px 8px", fontSize: 11.5, color: "var(--faint)" }}>—</td>;
  }
  return (
    <td
      className="eci-col-stage mono"
      style={{ padding: "6px 8px", fontSize: 11.5 }}
      title={`${s.electors.toLocaleString("en-IN")} electors, as of ${s.as_of ?? "unknown date"}`}
    >
      {s.approx ? "≈" : ""}{countIndian(s.electors)}
      <div style={{ fontSize: 10.5, color: "var(--faint)" }}>{formatLooseDate(s.as_of)}</div>
    </td>
  );
}

/** The table view of the state grid — always one tap away, and the default under 480px
 *  (PHASES-3-5-DECISIONS.md; PHASE3-SPEC.md §3.4). No totals row: the cited national totals are the ones
 *  in NationalSummary, and a sum across mixed dates isn't ours to make. */
export function StateTable({ regions, metric }: { regions: EciRegionSummary[]; metric: EciMetricDef }) {
  const withMetric = regions.filter((r) => r.metrics[metric.id]);
  const noMeasure = regions.filter((r) => r.has_figures && !r.metrics[metric.id]);
  const empty = regions.filter((r) => !r.has_figures);

  withMetric.sort((a, b) => {
    const va = metric.encode(a.metrics[metric.id]!);
    const vb = metric.encode(b.metrics[metric.id]!);
    return vb - va || a.name.localeCompare(b.name);
  });
  noMeasure.sort((a, b) => a.name.localeCompare(b.name));
  empty.sort((a, b) => a.name.localeCompare(b.name));

  return (
    <div className="nr-xscroll nr-xscroll-cue" style={{ borderRadius: 12 }}>
      <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 12.5 }}>
        <caption style={{ textAlign: "left", fontSize: 11.5, color: "var(--muted)", padding: "0 2px 8px" }}>
          SIR figures by State/UT — sorted by {metric.shortLabel}
        </caption>
        <thead>
          <tr style={{ borderBottom: "1px solid var(--rule)" }}>
            <th scope="col" style={{ textAlign: "left", padding: "6px 8px" }}>State/UT</th>
            <th scope="col" style={{ textAlign: "left", padding: "6px 8px" }}>Phase</th>
            <th scope="col" className="eci-col-stage" style={{ textAlign: "left", padding: "6px 8px" }}>Before SIR</th>
            <th scope="col" className="eci-col-stage" style={{ textAlign: "left", padding: "6px 8px" }}>Draft</th>
            <th scope="col" className="eci-col-stage" style={{ textAlign: "left", padding: "6px 8px" }}>Final</th>
            <th scope="col" style={{ textAlign: "right", padding: "6px 8px" }}>{metric.shortLabel} (count)</th>
            <th scope="col" style={{ textAlign: "right", padding: "6px 8px" }}>{metric.shortLabel} (%)</th>
          </tr>
        </thead>
        <tbody>
          {withMetric.map((r) => {
            const m = r.metrics[metric.id]!;
            return (
              <tr key={r.slug} style={{ borderBottom: "1px solid var(--rule2)" }}>
                <th scope="row" style={{ textAlign: "left", padding: "6px 8px", fontWeight: 500 }}>
                  <Link href={`/eci-files/numbers/${r.slug}`} style={{ color: "var(--eci-ink)", textDecoration: "none" }}>{r.name}</Link>
                </th>
                <td style={{ padding: "6px 8px" }}>{r.exercise === "special_revision" ? "SR" : romanPhase(r.phase)}</td>
                <StageCell region={r} stage="before" />
                <StageCell region={r} stage="draft" />
                <StageCell region={r} stage="final" />
                <td className="mono" style={{ textAlign: "right", padding: "6px 8px" }}>
                  {m.approx ? countIndianRough(m.count) : countIndian(Math.abs(m.count))}
                  {m.computed && <span style={{ marginLeft: 5, fontSize: 10, color: "var(--muted)" }}>computed</span>}
                  {m.approx && <span style={{ marginLeft: 5, fontSize: 10, color: "var(--muted)" }}>rounded</span>}
                </td>
                <td className="mono" style={{ textAlign: "right", padding: "6px 8px" }}>
                  {formatPercent(m.value, metric.id === "net_change")}
                </td>
              </tr>
            );
          })}
          {noMeasure.map((r) => (
            <tr key={r.slug} style={{ borderBottom: "1px solid var(--rule2)" }}>
              <th scope="row" style={{ textAlign: "left", padding: "6px 8px", fontWeight: 500 }}>
                <Link href={`/eci-files/numbers/${r.slug}`} style={{ color: "var(--eci-ink)", textDecoration: "none" }}>{r.name}</Link>
              </th>
              <td style={{ padding: "6px 8px" }}>{r.exercise === "special_revision" ? "SR" : romanPhase(r.phase)}</td>
              <StageCell region={r} stage="before" />
              <StageCell region={r} stage="draft" />
              <StageCell region={r} stage="final" />
              <td colSpan={2} style={{ padding: "6px 8px", fontSize: 11.5, color: "var(--muted)" }}>{metric.missingReason(r)}</td>
            </tr>
          ))}
          {empty.length > 0 && (
            <tr>
              <td colSpan={7} style={{ padding: "10px 8px", fontSize: 12, color: "var(--muted)" }}>
                No figures yet in the record:{" "}
                {empty.map((r, i) => (
                  <span key={r.slug}>
                    <Link href={`/eci-files/numbers/${r.slug}`} style={{ color: "var(--accent-2)" }}>{r.name}</Link>
                    {i < empty.length - 1 ? ", " : ""}
                  </span>
                ))}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
