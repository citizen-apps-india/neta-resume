import Link from "next/link";
import type { EciEntry } from "@/types/eci-files";
import { eciStatusMeta, formatEciDate } from "@/lib/eci-files";

/** The slim key-moments strip (REDESIGN brief): each card is a lane-coloured left border, the date, the
 *  title, and the status word — no chip box and no "checked" tick here, unlike the full `StatusWord`,
 *  since a moment card's job is one glance, not the drawer's provenance detail. */
export function FrontKeyMoments({ moments }: { moments: EciEntry[] }) {
  if (moments.length === 0) return null;
  return (
    <section>
      <div style={{ display: "flex", flexDirection: "column", gap: 3, marginBottom: 12 }}>
        <h2 className="mono" style={{ fontSize: 11, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--faint)", margin: 0 }}>
          Key moments
        </h2>
        <span style={{ fontSize: 13, color: "var(--muted)" }}>
          {moments.length} dates that explain the shape of the record
        </span>
      </div>
      <div className="eci-front-moments">
        {moments.map((m) => (
          <Link
            key={m.id}
            href={`/eci-files/timeline?entry=${encodeURIComponent(m.id)}`}
            className="tap"
            style={{
              display: "flex", flexDirection: "column", gap: 6, padding: "10px 12px", borderRadius: 8,
              borderLeft: `3px solid var(--eci-lane-${m.lane})`, background: "var(--card)", textDecoration: "none", color: "var(--ink)",
            }}
          >
            <span className="mono" style={{ fontSize: 10.5, color: "var(--muted)" }}>{formatEciDate(m.date, m.date_precision)}</span>
            <span style={{ fontSize: 12.5, fontWeight: 650, lineHeight: 1.32 }}>{m.title}</span>
            <span className="mono" style={{ fontSize: 10.5, color: "var(--muted)" }}>{eciStatusMeta(m.status).label}</span>
          </Link>
        ))}
      </div>
    </section>
  );
}
