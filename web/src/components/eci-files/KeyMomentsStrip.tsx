import Link from "next/link";
import type { EciEntry } from "@/types/eci-files";
import { formatEciDate } from "@/lib/eci-files";
import { StatusChip } from "@/components/eci-files/StatusChip";

/** ~8 entries, horizontal, on one axis (REDESIGN-SPEC §"Web") — each a doorway into the lane timeline,
 *  deep-linked via `?entry=<id>` so tapping one opens the drawer with the window already centred on it. */
export function KeyMomentsStrip({ moments }: { moments: EciEntry[] }) {
  if (moments.length === 0) return null;
  return (
    <section style={{ marginBottom: 32 }}>
      <h2 className="mono" style={{ fontSize: 11, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--faint)", margin: "0 0 12px" }}>
        Key moments
      </h2>
      <div className="nr-xscroll nr-xscroll-cue eci-moments" style={{ display: "flex", gap: 12, paddingBottom: 4 }}>
        {moments.map((m) => (
          <Link
            key={m.id}
            href={`/eci-files/timeline?entry=${encodeURIComponent(m.id)}`}
            className="lift tap"
            style={{
              flex: "0 0 auto", width: 220, textDecoration: "none", color: "var(--ink)",
              border: "1px solid var(--rule)", borderRadius: 12, background: "var(--card2)", padding: "14px 15px",
              display: "flex", flexDirection: "column", gap: 8,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
              <span className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>{formatEciDate(m.date, m.date_precision)}</span>
              <StatusChip status={m.status} />
            </div>
            <div className="serif" style={{ fontSize: 13.5, fontWeight: 600, lineHeight: 1.35 }}>{m.title}</div>
          </Link>
        ))}
      </div>
    </section>
  );
}
