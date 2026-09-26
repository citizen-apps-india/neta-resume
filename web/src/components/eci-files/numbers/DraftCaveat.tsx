import { formatLooseDate } from "@/lib/eci-files";

/** "A draft roll is not the final roll" — one line, plus the longer reasoning behind a "Why draft ≠
 *  final" disclosure (docs/eci-files/designs/B-After-Numbers.dc.html, B-Phone-Numbers.dc.html), repeated
 *  on both /numbers and every state page (PHASE3-SPEC.md §3.3/§3.6). */
export function DraftCaveat({ lastAsOf }: { lastAsOf?: string | null }) {
  return (
    <div className="eci-caveat" style={{ marginBottom: 24, display: "flex", flexDirection: "column", gap: 10 }}>
      <p style={{ margin: 0, fontSize: 14, color: "var(--ink2)", lineHeight: 1.5 }}>
        A draft roll is not the final roll — names still return through claims and appeals.
      </p>
      <details className="eci-more">
        <summary
          className="mono"
          style={{ listStyle: "none", cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 6, fontSize: 13.5, fontWeight: 600, color: "var(--eci-ink)" }}
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true" style={{ flexShrink: 0 }}>
            <path d="M3.5 4.5L6 7.5L8.5 4.5" stroke="var(--eci-ink)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Why draft ≠ final
        </summary>
        <div style={{ padding: "10px 0 0 18px", fontSize: 13, lineHeight: 1.6, color: "var(--ink2)", maxWidth: "64ch" }}>
          <p style={{ margin: lastAsOf ? "0 0 8px" : 0 }}>
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
      </details>
    </div>
  );
}
