import type { ReactNode } from "react";
import Link from "next/link";

/** A bento headline-stat card: optional icon chip, big mono value, label. `tone="hero"` gives the primary
 *  metric an accent-soft treatment. Lifts on hover; becomes a link when `href` is set. Token-only. */
export function StatCard({
  value, label, icon, tone = "default", href, hint,
}: {
  value: ReactNode;
  label: string;
  icon?: ReactNode;
  tone?: "default" | "hero";
  href?: string;
  hint?: ReactNode;
}) {
  const hero = tone === "hero";
  const style: React.CSSProperties = {
    display: "block", padding: "17px 18px 15px", borderRadius: 14, textDecoration: "none", color: "var(--ink)",
    border: `1px solid ${hero ? "var(--accent-soft-bd)" : "var(--rule)"}`,
    background: hero ? "var(--accent-soft)" : "var(--card2)",
  };
  const inner = (
    <>
      {icon && (
        <div style={{ width: 32, height: 32, borderRadius: 9, display: "grid", placeItems: "center", fontSize: 15, marginBottom: 12, background: hero ? "var(--card2)" : "var(--accent-soft)", color: hero ? "var(--accent)" : "var(--accent-soft-fg)", border: hero ? "1px solid var(--accent-soft-bd)" : "none" }}>{icon}</div>
      )}
      <div className="mono" style={{ fontSize: "clamp(23px,4.2vw,32px)", fontWeight: 700, lineHeight: 1, color: hero ? "var(--accent-soft-fg)" : "var(--ink)" }}>{value}</div>
      <div style={{ fontSize: 12, color: hero ? "var(--accent-soft-fg)" : "var(--muted)", marginTop: 9, letterSpacing: "0.01em" }}>{label}</div>
      {hint && <div style={{ fontSize: 11, color: "var(--faint)", marginTop: 3 }}>{hint}</div>}
    </>
  );
  return href
    ? <Link href={href} className="liftsm" style={style}>{inner}</Link>
    : <div className="liftsm" style={style}>{inner}</div>;
}
