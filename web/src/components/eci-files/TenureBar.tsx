import type { EciTenure } from "@/types/eci-files";
import { ECI_TENURE_AXIS, dateFraction, formatLooseDate, tenureSegments } from "@/lib/eci-files";

const KIND_LABEL: Record<string, string> = { ec: "EC", cec: "CEC", other: "" };

function segmentClass(kind: string): string {
  return kind === "cec" ? "eci-tenure-cec" : kind === "ec" ? "eci-tenure-ec" : "eci-tenure-other";
}

/** A person's tenure(s) as bars on the shared `ECI_TENURE_AXIS` — the same geometry
 *  `CommissionTenureChart` draws per row, `tenureSegments()` (PHASE4-SPEC.md §2.5). A tenure with only
 *  `to` set (no `from` on record) draws a 2px tick instead of a bar, labelled "until {date}". */
export function TenureBar({
  tenure, axis = ECI_TENURE_AXIS, height = 14, showLabels = false,
}: {
  tenure: EciTenure[] | null | undefined;
  axis?: { from: string; to: string };
  height?: number;
  showLabels?: boolean;
}) {
  const segments = tenureSegments(tenure, axis);
  const ticks = (tenure ?? []).filter((t) => !t.from && t.to);

  if (segments.length === 0 && ticks.length === 0) {
    return <p style={{ fontSize: 12.5, color: "var(--muted)", margin: 0 }}>Tenure dates not on record</p>;
  }

  const label = segments
    .map((s) => `${s.office || "Office"} ${s.clippedStart ? "from before 2019" : formatLooseDate(s.from)} – ${s.openEnd ? "present" : formatLooseDate(s.to)}`)
    .join("; ");

  return (
    <svg
      viewBox={`0 0 1000 ${height}`}
      width="100%"
      height={height}
      preserveAspectRatio="none"
      className="eci-tenure-bar"
      role="img"
      aria-label={label || "Tenure"}
    >
      {segments.map((s, i) => {
        const x0 = s.x0 * 1000;
        const x1 = s.x1 * 1000;
        const w = Math.max(2, x1 - x0);
        return (
          <g key={i}>
            <rect x={x0} y={0} width={w} height={height} rx={s.openEnd ? 0 : Math.min(3, height / 3)} className={segmentClass(s.kind)} />
            {s.clippedStart && (
              <text x={x0 + 2} y={height - 3} fontSize={Math.min(9, height * 0.6)} fill="var(--faint)">◂</text>
            )}
            {showLabels && (
              <text x={x0 + 4} y={height / 2 + 4} fontSize={Math.min(10, height * 0.7)} fill={s.kind === "cec" ? "var(--card)" : "var(--ink)"}>
                {KIND_LABEL[s.kind]}
              </text>
            )}
          </g>
        );
      })}
      {ticks.map((t, i) => {
        const x = dateFraction(t.to as string, axis.from, axis.to) * 1000;
        return <rect key={`tick-${i}`} x={x - 1} y={0} width={2} height={height} className="eci-tenure-other" />;
      })}
    </svg>
  );
}
