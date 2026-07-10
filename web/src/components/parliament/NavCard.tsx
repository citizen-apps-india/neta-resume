import Link from "next/link";

/** An "explore" nav card — icon chip + label + short description. Replaces the passive plain-border action
 *  links on the dashboard; lifts on hover. `href` carries the current house param. Token-only. */
export function NavCard({ href, icon, label, desc }: { href: string; icon: string; label: string; desc?: string }) {
  return (
    <Link
      href={href}
      className="liftsm"
      style={{ display: "flex", alignItems: "center", gap: 12, padding: "13px 15px", borderRadius: 12, border: "1px solid var(--rule)", background: "var(--card2)", textDecoration: "none", color: "var(--ink)" }}
    >
      <span style={{ width: 34, height: 34, borderRadius: 9, display: "grid", placeItems: "center", background: "var(--accent-soft)", color: "var(--accent-soft-fg)", fontSize: 16, flexShrink: 0 }}>{icon}</span>
      <span style={{ display: "flex", flexDirection: "column", minWidth: 0 }}>
        <span style={{ fontSize: 13.5, fontWeight: 600 }}>{label}</span>
        {desc && <span style={{ fontSize: 11.5, color: "var(--muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{desc}</span>}
      </span>
    </Link>
  );
}
