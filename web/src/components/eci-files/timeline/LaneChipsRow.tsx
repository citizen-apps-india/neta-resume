import type { EciFilesLane, EciLaneCount } from "@/types/eci-files";
import { ECI_LANE_ORDER, eciLaneLabel } from "@/lib/eci-files";

/** The lane toggle chips shared by the desktop control bar and the phone chip row (DESIGN-BRIEF: "lane
 *  toggle chips with counts"). Counts are whole-record (the API's `lanes` facet ignores the date window
 *  and every other filter), so they read the same no matter what's currently visible below. */
export function LaneChipsRow({
  lanes, active, onToggle, short = false,
}: {
  lanes: EciLaneCount[];
  active: Set<EciFilesLane>;
  onToggle: (lane: EciFilesLane) => void;
  short?: boolean;
}) {
  const byLane = new Map(lanes.map((l) => [l.lane, l.count]));
  return (
    <div role="group" aria-label="Lanes" style={{ display: "flex", gap: 8, flexWrap: short ? "nowrap" : "wrap", overflowX: short ? "auto" : undefined, alignItems: "center" }}>
      {!short && <span className="mono" style={{ fontSize: 11, color: "var(--muted)", marginRight: 2 }}>Lanes</span>}
      {ECI_LANE_ORDER.map((lane) => {
        const pressed = active.has(lane);
        const label = short ? eciLaneLabel(lane).replace(" the Commission", "") : eciLaneLabel(lane);
        return (
          <button
            key={lane}
            type="button"
            aria-pressed={pressed}
            onClick={() => onToggle(lane)}
            className="tap"
            style={{
              display: "inline-flex", alignItems: "center", gap: 7, padding: "0 12px", minHeight: 36,
              borderRadius: 999, border: `1px solid ${pressed ? "var(--border)" : "var(--rule)"}`,
              background: pressed ? "var(--card)" : "var(--sunken)", fontSize: 13, color: pressed ? "var(--ink)" : "var(--muted)",
              cursor: "pointer", flexShrink: 0, whiteSpace: "nowrap",
            }}
          >
            <span aria-hidden style={{ width: 9, height: 9, borderRadius: "50%", background: `var(--eci-lane-${lane})`, opacity: pressed ? 1 : 0.4, display: "inline-block" }} />
            {label}
            {!short && <span className="mono" style={{ fontSize: 11.5, color: "var(--muted)" }}>{byLane.get(lane) ?? 0}</span>}
          </button>
        );
      })}
    </div>
  );
}
