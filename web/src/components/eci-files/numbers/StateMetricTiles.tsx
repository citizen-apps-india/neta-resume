import { countIndian } from "@/lib/format";
import { formatPercent } from "@/lib/eci-numbers";
import type { EciRegionSummary, EciStateMetric } from "@/types/eci-files";

type MetricKey = "draft_left_off" | "net_change" | "appeals_filed";

/** appeals_filed is a state-page-only tile (PHASES-3-5-DECISIONS.md: "Shown on state pages only, not as a
 *  tile measure") — kept here, out of eci-numbers.ts's ECI_METRICS. */
const TILES: { key: MetricKey; label: string; signed: boolean; missing: (r: EciRegionSummary) => string }[] = [
  { key: "draft_left_off", label: "Left off the draft roll", signed: false, missing: (r) => (r.stages.some((s) => s.stage === "before") ? "no draft figure" : "no pre-SIR figure") },
  { key: "net_change", label: "Net change to the final roll", signed: true, missing: () => "no final roll yet" },
  { key: "appeals_filed", label: "Appeals filed against the final roll", signed: false, missing: () => "no appeals figure" },
];

function TileValue({ m, signed }: { m: EciStateMetric; signed: boolean }) {
  return (
    <>
      <div className="mono eci-hero-value" style={{ fontSize: 22 }}>
        {formatPercent(m.value, signed)}{(m.approx || m.computed) && "*"}
      </div>
      <div style={{ fontSize: 11.5, color: "var(--ink2)" }}>{countIndian(Math.abs(m.count))} of {countIndian(m.base)}</div>
    </>
  );
}

/** Three metric tiles on the state page — draft_left_off, net_change and (state-page-only) appeals_filed
 *  (PHASE3-SPEC.md §3.6). Omitted when the region has no stages at all. */
export function StateMetricTiles({ region }: { region: EciRegionSummary }) {
  if (!region.has_figures) return null;
  return (
    <div className="nr-statgrid" style={{ marginBottom: 26 }}>
      {TILES.map(({ key, label, signed, missing }) => {
        const m = region.metrics[key];
        return (
          <div key={key} className="eci-hero-tile" style={{ borderRadius: 14 }}>
            <div style={{ fontSize: 11.5, color: "var(--muted)", marginBottom: 6 }}>{label}</div>
            {m ? <TileValue m={m} signed={signed} /> : <div style={{ fontSize: 13, color: "var(--muted)" }}>— {missing(region)}</div>}
          </div>
        );
      })}
    </div>
  );
}
