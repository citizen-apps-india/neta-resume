import type { CSSProperties } from "react";
import type { EciRegionSummary } from "@/types/eci-files";

const srOnly: CSSProperties = {
  position: "absolute", width: 1, height: 1, padding: 0, margin: -1, overflow: "hidden",
  clip: "rect(0,0,0,0)", whiteSpace: "nowrap", border: 0,
};

type PickerRegion = Pick<EciRegionSummary, "slug" | "name" | "has_figures" | "exercise" | "stages">;

/** A region whose only figure is the pre-SIR `before` baseline — real, but not SIR progress (no draft
 *  or final roll yet), so it shouldn't sit in "With SIR figures" alongside states with an actual draft
 *  or final roll on record. */
function isBeforeOnly(r: PickerRegion): boolean {
  return r.stages.length === 1 && r.stages[0].stage === "before";
}

/** The "What happened in my state?" entry point (PHASE3-SPEC.md §3.3/§3.4/§3.5) — a plain GET form, so
 *  it works with no client JS: submitting lands on `/eci-files/numbers?state=<slug>`, which redirects to
 *  the state page server-side. No auto-navigate on `change` (arrow keys fire it in some browsers). */
export function StatePicker({
  regions, current, compact,
}: {
  regions: PickerRegion[];
  current?: string;
  compact?: boolean;
}) {
  const byName = (a: PickerRegion, b: PickerRegion) => a.name.localeCompare(b.name);
  const withFigures = regions
    .filter((r) => r.has_figures && r.exercise !== "special_revision" && !isBeforeOnly(r))
    .slice().sort(byName);
  const baselineOnly = regions
    .filter((r) => r.has_figures && (r.exercise === "special_revision" || isBeforeOnly(r)))
    .slice().sort(byName);
  const withoutFigures = regions.filter((r) => !r.has_figures).slice().sort(byName);

  return (
    <form action="/eci-files/numbers" method="get" className="eci-picker">
      <label htmlFor="eci-state-picker" style={compact ? srOnly : { fontSize: 12.5, color: "var(--ink2)" }}>
        What happened in my state?
      </label>
      <select id="eci-state-picker" name="state" className="eci-select" required defaultValue={current ?? ""}>
        <option value="" disabled>Choose a State or UT</option>
        {withFigures.length > 0 && (
          <optgroup label="With SIR figures">
            {withFigures.map((r) => <option key={r.slug} value={r.slug}>{r.name}</option>)}
          </optgroup>
        )}
        {baselineOnly.length > 0 && (
          <optgroup label="Baseline or Special Revision only">
            {baselineOnly.map((r) => <option key={r.slug} value={r.slug}>{r.name}</option>)}
          </optgroup>
        )}
        {withoutFigures.length > 0 && (
          <optgroup label="No figures yet">
            {withoutFigures.map((r) => <option key={r.slug} value={r.slug}>{r.name}</option>)}
          </optgroup>
        )}
      </select>
      <button
        type="submit"
        className="tap btnGhost"
        style={{ fontSize: 12.5, padding: "7px 14px", borderRadius: 8, border: "1px solid var(--border)", background: "none", cursor: "pointer", color: "var(--ink)" }}
      >
        Show
      </button>
    </form>
  );
}
