"use client";

import { useState } from "react";
import type { EciEntry } from "@/types/eci-files";
import { eciEntryHref, formatEciDate } from "@/lib/eci-files";
import { EntryRow } from "@/components/eci-files/ui/EntryRow";

const PAGE = 6;

function byDateDesc(a: EciEntry, b: EciEntry): number {
  if (!a.date && !b.date) return 0;
  if (!a.date) return 1;
  if (!b.date) return -1;
  return a.date < b.date ? 1 : a.date > b.date ? -1 : 0;
}

function breakdown(claims: number, responses: number): string | null {
  const parts: string[] = [];
  if (claims > 0) parts.push(`${claims} claim${claims === 1 ? "" : "s"}`);
  if (responses > 0) parts.push(`${responses} response${responses === 1 ? "" : "s"}`);
  return parts.length > 0 ? parts.join(" and ") : null;
}

/** "His objections and decisions" (C-After-Profile.dc.html, C-Phone-Profile.dc.html): every entry that
 *  names this person, newest first, as one compact `EntryRow` list — replacing the three separate
 *  decisions/mentions/responses sections and the lane-dot timeline with the single hierarchy the brief
 *  asks for (§3 "Hierarchy": one hero, then scannable rows of equal weight). Collapsed to the first
 *  {@link PAGE} rows behind a "+N more" line that names how many of the rest are claims or responses, so
 *  the fold never hides what kind of record is behind it. */
export function PersonRecordList({ entries, basePath }: { entries: EciEntry[]; basePath: string }) {
  const [expanded, setExpanded] = useState(false);
  if (entries.length === 0) return null;

  const sorted = [...entries].sort(byDateDesc);
  const shown = expanded ? sorted : sorted.slice(0, PAGE);
  const hidden = sorted.slice(PAGE);
  const more = breakdown(
    hidden.filter((e) => e.status === "claim").length,
    hidden.filter((e) => e.status === "response").length,
  );

  return (
    <section id="record">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 10 }}>
        <h2 className="serif" style={{ fontSize: 17, fontWeight: 650, margin: 0 }}>Objections and decisions</h2>
        <span className="mono" style={{ fontSize: 11.5, color: "var(--muted)" }}>{sorted.length} on record</span>
      </div>
      <div style={{ border: "1px solid var(--rule)", borderRadius: 12, background: "var(--card)", padding: "0 18px" }}>
        {shown.map((e) => (
          <EntryRow
            key={e.id}
            date={formatEciDate(e.date, e.date_precision)}
            lane={e.lane}
            title={e.title}
            href={eciEntryHref(e.id, {}, basePath)}
            status={e.status}
            checked={e.check_status === "checked"}
          />
        ))}
        {!expanded && hidden.length > 0 && (
          <button
            type="button"
            className="tap"
            onClick={() => setExpanded(true)}
            aria-expanded={expanded}
            style={{ display: "block", margin: "10px 0 14px", border: 0, background: "none", padding: 0, fontSize: 12.5, color: "var(--accent-2)", cursor: "pointer" }}
          >
            + {hidden.length} more{more ? `, including ${more}` : ""}
          </button>
        )}
      </div>
    </section>
  );
}
