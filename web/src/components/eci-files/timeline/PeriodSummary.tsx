import type { EciCompactEntry, EciFilesLane } from "@/types/eci-files";
import { ECI_LANE_ORDER, eciLaneLabel } from "@/lib/eci-files";

function absentLanesText(absent: string[]): string | null {
  if (absent.length === 0) return null;
  if (absent.length === 1) return `No ${absent[0]} in this period`;
  return `No ${absent.slice(0, -1).join(", ")} or ${absent[absent.length - 1]} in this period`;
}

/** The period card: counts per lane and a stacked bar — no generated prose sentence (DESIGN-BRIEF §4:
 *  "numbers beat words"). Scoped to the server-filtered window/topic/person, not the lane chips or search
 *  (those only hide rows below; the period is a fact about the record, not about the current view). */
export function PeriodSummary({ periodLabel, entries }: { periodLabel: string; entries: EciCompactEntry[] }) {
  const counts = new Map<EciFilesLane, number>();
  for (const e of entries) counts.set(e.lane, (counts.get(e.lane) ?? 0) + 1);
  const checked = entries.filter((e) => e.check_status === "checked").length;
  const total = entries.length;

  const present = ECI_LANE_ORDER.filter((l) => (counts.get(l) ?? 0) > 0);
  const absent = ECI_LANE_ORDER.filter((l) => (counts.get(l) ?? 0) === 0).map((l) => eciLaneLabel(l));
  const absentText = absentLanesText(absent);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14, background: "var(--card)", border: "1px solid var(--rule)", borderRadius: 14, padding: "18px 20px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 12, flexWrap: "wrap" }}>
        <h2 style={{ margin: 0, fontSize: 20, fontWeight: 650 }}>{periodLabel}</h2>
        <span className="mono" style={{ fontSize: 12, color: "var(--muted)" }}>
          {total} {total === 1 ? "entry" : "entries"} · {checked} checked
        </span>
      </div>

      {total > 0 && (
        <div style={{ display: "flex", borderRadius: 4, overflow: "hidden", gap: 2 }}>
          {present.map((l) => (
            <span key={l} aria-hidden style={{ display: "block", height: 8, background: `var(--eci-lane-${l})`, width: `${((counts.get(l) ?? 0) / total) * 100}%` }} />
          ))}
        </div>
      )}

      <div style={{ display: "flex", gap: 16, flexWrap: "wrap", fontSize: 12.5, color: "var(--ink2)" }}>
        {present.map((l) => (
          <span key={l}>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 11, fontWeight: 600, color: `var(--eci-lane-${l})` }}>
              <span aria-hidden style={{ width: 8, height: 8, borderRadius: "50%", background: `var(--eci-lane-${l})`, display: "inline-block" }} />
              {eciLaneLabel(l)}
            </span>{" "}
            {counts.get(l)}
          </span>
        ))}
        {absentText && <span style={{ color: "var(--muted)" }}>{absentText}</span>}
        {total === 0 && <span style={{ color: "var(--muted)" }}>No entries match the current filters in this period.</span>}
      </div>
    </div>
  );
}
