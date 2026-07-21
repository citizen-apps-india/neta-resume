"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";
import { Frame } from "@/components/ui";

/** One switchable legislator card (the MP or the MLA) plus the header text that goes with it. */
export type PreviewPanel = {
  key: string;
  tab: string;            // segmented-control label, e.g. "Lok Sabha MP"
  lead: string;           // header lead, e.g. "Your area’s MP"
  place: string | null;   // constituency pill
  url: string;            // browser-frame URL
  card: ReactNode;        // server-rendered PreviewCard
};

/** Client shell for the homepage preview: renders the browser-frame, the "Your area" header, and — when
 *  there's more than one panel (MP + MLA) — a segmented toggle that swaps which card is shown. With a
 *  single panel it renders exactly the pre-toggle widget. Cards are server-rendered and passed in as
 *  props, so switching is pure client show/hide (no refetch). */
export function HomePreviewToggle({ panels, precise }: { panels: PreviewPanel[]; precise: boolean }) {
  const [active, setActive] = useState(0);
  const panel = panels[active] ?? panels[0];
  const multi = panels.length > 1;

  return (
    <>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0 }}>
          <span style={{ fontSize: 12.5, color: "var(--muted)" }}>{panel.lead}</span>
          {panel.place && (
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "4px 11px", borderRadius: 999, background: "var(--accent-soft)", color: "var(--accent-soft-fg)", fontSize: 12.5, fontWeight: 600 }}>
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: "currentColor" }} />
              {panel.place}
            </span>
          )}
        </div>
        {precise && (
          <Link href="/directory" className="navlink" style={{ fontSize: 12, color: "var(--muted)" }}>
            Not you? Search →
          </Link>
        )}
      </div>

      {multi && (
        <div
          role="tablist"
          aria-label="Choose legislator"
          style={{ display: "inline-flex", padding: 3, gap: 3, marginBottom: 14, background: "var(--sunken)", border: "1px solid var(--rule)", borderRadius: 999 }}
        >
          {panels.map((p, i) => {
            const on = i === active;
            return (
              <button
                key={p.key}
                role="tab"
                aria-selected={on}
                onClick={() => setActive(i)}
                className="seg tap"
                style={{
                  border: "none", cursor: "pointer", borderRadius: 999, padding: "6px 16px",
                  fontSize: 12.5, fontWeight: 600,
                  background: on ? "var(--card)" : "transparent",
                  color: on ? "var(--ink)" : "var(--muted)",
                  boxShadow: on ? "0 1px 3px -1px var(--shadow)" : "none",
                }}
              >
                {p.tab}
              </button>
            );
          })}
        </div>
      )}

      <Frame url={panel.url}>{panel.card}</Frame>
    </>
  );
}
