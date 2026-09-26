import type { EciFilesLane } from "@/types/eci-files";
import { eciLaneLabel } from "@/lib/eci-files";

/** The lane as a coloured dot plus its name: the one place colour identifies the kind of event. */
export function LaneChip({ lane, short = false, size = 12 }: { lane: EciFilesLane; short?: boolean; size?: number }) {
  const label = short ? eciLaneLabel(lane).replace(" the Commission", "") : eciLaneLabel(lane);
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: size, fontWeight: 600, color: `var(--eci-lane-${lane})` }}>
      <span aria-hidden style={{ width: 8, height: 8, borderRadius: "50%", background: `var(--eci-lane-${lane})`, display: "inline-block" }} />
      {label}
    </span>
  );
}
