import Link from "next/link";
import type { ReactNode } from "react";
import type { EciEntryStatus, EciFilesLane } from "@/types/eci-files";
import { LaneChip } from "@/components/eci-files/ui/LaneChip";
import { StatusWord } from "@/components/eci-files/ui/StatusWord";

/** One entry as a scannable row: date, lane, the headline as a link, and how it's sourced. `extra` sits on the
 *  status line (e.g. "+2 more records of this"); `emphasis` marks a key moment. The headline is a real
 *  `<a href>` when `href` is given, or a real `<button>` when `onClick` is given instead (the timeline's
 *  in-place expand: a state change, not a navigation, so a button is the honest element for it). */
export function EntryRow({
  date, lane, title, href, onClick, status, checked, extra, emphasis = false,
}: {
  date: string;
  lane: EciFilesLane;
  title: string;
  href?: string;
  onClick?: () => void;
  status: EciEntryStatus;
  checked: boolean;
  extra?: ReactNode;
  emphasis?: boolean;
}) {
  const titleStyle = { fontSize: emphasis ? 20 : 16, fontWeight: emphasis ? 650 : 600, lineHeight: 1.3, color: "var(--ink)" };
  return (
    <article style={{ display: "grid", gridTemplateColumns: "64px minmax(0, 1fr)", gap: 16, padding: "14px 0", borderTop: "1px solid var(--rule)" }}>
      <div className="mono" style={{ fontSize: 12.5, color: "var(--muted)", paddingTop: 2 }}>{date}</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 6, minWidth: 0 }}>
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <LaneChip lane={lane} />
          {emphasis && <span className="mono" style={{ fontSize: 10.5, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--eci-ink)" }}>Key moment</span>}
        </div>
        {onClick ? (
          <button
            type="button"
            onClick={onClick}
            style={{ ...titleStyle, fontFamily: "inherit", textAlign: "left", border: 0, background: "none", padding: 0, cursor: "pointer" }}
          >
            {title}
          </button>
        ) : (
          <Link href={href ?? "#"} scroll={false} style={{ ...titleStyle, textDecoration: "none" }}>
            {title}
          </Link>
        )}
        <div style={{ display: "flex", gap: 14, alignItems: "center", flexWrap: "wrap" }}>
          <StatusWord status={status} checked={checked} />
          {extra}
        </div>
      </div>
    </article>
  );
}
