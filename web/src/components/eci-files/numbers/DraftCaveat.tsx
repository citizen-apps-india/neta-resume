import { formatLooseDate } from "@/lib/eci-files";

/** "A draft roll is not the final roll" — the caveat repeated on both /numbers and every state page
 *  (PHASE3-SPEC.md §3.3/§3.6). */
export function DraftCaveat({ lastAsOf }: { lastAsOf?: string | null }) {
  return (
    <div className="eci-caveat" style={{ marginBottom: 24 }}>
      <div className="serif" style={{ fontSize: 14.5, fontWeight: 600, marginBottom: 6 }}>A draft roll is not the final roll</div>
      <p style={{ fontSize: 13, color: "var(--ink2)", lineHeight: 1.55, margin: "0 0 8px", maxWidth: "72ch" }}>
        The draft roll is published after enumeration. Names left off it can come back through claims and
        objections, and new electors are added, before the final roll is published. So the share left off
        the draft is usually larger than the net change from the pre-SIR roll to the final roll. Where a
        final roll isn&apos;t in the record yet, only the draft measure can be shown.
      </p>
      {lastAsOf && (
        <p className="mono" style={{ fontSize: 11, color: "var(--muted)", margin: 0 }}>
          Figures run to {formatLooseDate(lastAsOf)}. Several final rolls were still pending then.
        </p>
      )}
    </div>
  );
}
