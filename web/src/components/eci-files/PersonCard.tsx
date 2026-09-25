import Link from "next/link";
import type { EciPersonSummary } from "@/types/eci-files";

/** A card per person on /eci-files/people: name, role, tenure, and how many entries name them. */
export function PersonCard({ p }: { p: EciPersonSummary }) {
  return (
    <Link
      href={`/eci-files/people/${p.slug}`}
      className="lift"
      style={{
        display: "block", textDecoration: "none", color: "var(--ink)",
        border: "1px solid var(--rule)", borderRadius: 12, background: "var(--card2)", padding: "16px 18px",
      }}
    >
      <div className="serif" style={{ fontSize: 16.5, fontWeight: 600 }}>{p.name}</div>
      <div style={{ fontSize: 12.5, color: "var(--ink2)", marginTop: 4 }}>{p.role ?? "—"}</div>
      <div style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 2 }}>{p.tenure ?? "—"}</div>
      <div className="mono" style={{ fontSize: 10.5, color: "var(--faint)", marginTop: 10 }}>
        {p.entry_count} entr{p.entry_count === 1 ? "y" : "ies"}
      </div>
    </Link>
  );
}
