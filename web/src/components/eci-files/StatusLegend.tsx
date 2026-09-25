import type { EciEntryStatus } from "@/types/eci-files";
import { ECI_STATUS_META } from "@/lib/eci-files";

const ORDER: EciEntryStatus[] = ["documented", "reported", "claim", "response"];

/** The four trust-colour key, plus what solid/hollow means. Required reading alongside the dots: two of
 *  the four tokens (claim, response) sit under 3:1 contrast on their own (REDESIGN-SPEC §"Identity"), so
 *  colour is never the only signal — this legend and the drawer's text status carry the rest. */
export function StatusLegend() {
  return (
    <div className="eci-legend" role="list" aria-label="Status colours">
      {ORDER.map((s) => {
        const m = ECI_STATUS_META[s];
        return (
          <span key={s} role="listitem" className="eci-legend-item">
            <span aria-hidden style={{ width: 10, height: 10, borderRadius: "50%", background: m.token, flexShrink: 0 }} />
            {m.label}
          </span>
        );
      })}
      <span className="eci-legend-item">
        <span aria-hidden style={{ width: 10, height: 10, borderRadius: "50%", border: "1.5px solid var(--muted)", flexShrink: 0 }} />
        Not yet checked (hollow)
      </span>
    </div>
  );
}
