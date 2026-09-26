import Link from "next/link";
import { ECI_METRIC_FOOTNOTE, metricValueText, type EciMetricDef } from "@/lib/eci-numbers";
import type { EciRegionSummary } from "@/types/eci-files";

const RANK_COUNT = 8;

/** The hero's ranked bar list (docs/eci-files/designs/B-After-Numbers.dc.html): the top 8 States/UTs on
 *  the current metric, as horizontal bars — the read the tile grid can't give at a glance. Each row opens
 *  the state page, same as a tile. Returns null when nothing on the current metric has a figure yet. */
export function RankedBarList({ regions, metric }: { regions: EciRegionSummary[]; metric: EciMetricDef }) {
  const withMetric = regions.filter((r) => r.metrics[metric.id]);
  if (withMetric.length === 0) return null;

  const ranked = withMetric
    .map((r) => ({ region: r, m: r.metrics[metric.id]!, encoded: metric.encode(r.metrics[metric.id]!) }))
    .sort((a, b) => b.encoded - a.encoded || a.region.name.localeCompare(b.region.name))
    .slice(0, RANK_COUNT);

  const max = Math.max(...ranked.map((r) => r.encoded), 1);
  const anyFlagged = ranked.some((r) => r.m.approx || r.m.computed);

  return (
    <section style={{ display: "flex", flexDirection: "column", gap: 14, background: "var(--card)", border: "1px solid var(--rule)", borderRadius: 14, padding: "22px 24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap", gap: 10 }}>
        <h2 className="serif" style={{ margin: 0, fontSize: 18, fontWeight: 650 }}>{metric.rankTitle}</h2>
        <span className="mono" style={{ fontSize: 11.5, color: "var(--muted)" }}>
          {ranked.length} of {withMetric.length} States/UTs with {metric.id === "net_change" ? "a final roll" : "a draft figure"} so far
        </span>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {ranked.map(({ region, m, encoded }) => (
          <Link
            key={region.slug}
            href={`/eci-files/numbers/${region.slug}`}
            className="tap"
            style={{ display: "grid", gridTemplateColumns: "minmax(120px,168px) minmax(0,1fr) 64px", gap: 10, alignItems: "center", textDecoration: "none", color: "inherit" }}
            aria-label={`${region.name}: ${metricValueText(metric, m)} — ${metric.label.toLowerCase()}. Open state page.`}
          >
            <span style={{ fontSize: 13.5, color: "var(--ink)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
              {region.name} <span className="mono" style={{ color: "var(--muted)", fontSize: 11 }}>{region.code}</span>
            </span>
            <span aria-hidden style={{ height: 14, borderRadius: 3, background: "var(--eci-ink)", width: `${Math.max(2, (encoded / max) * 100)}%`, display: "block" }} />
            <span className="mono" style={{ fontSize: 12.5, color: "var(--ink)", textAlign: "right" }}>{metricValueText(metric, m)}</span>
          </Link>
        ))}
      </div>
      {anyFlagged && <span className="mono" style={{ fontSize: 10.5, color: "var(--faint)" }}>{ECI_METRIC_FOOTNOTE}</span>}
    </section>
  );
}
