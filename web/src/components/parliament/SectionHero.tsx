import type { ReactNode } from "react";
import Link from "next/link";

/** Section header shared across the Parliament pages: a live pulse-dot eyebrow, serif title, subtitle, and a
 *  right-aligned slot (the house toggle). Sits over a soft local accent wash. Server component, token-only. */
export function SectionHero({
  eyebrow, title, subtitle, right, backHref, backLabel = "Parliament functioning",
}: {
  eyebrow: string;
  title: ReactNode;
  subtitle?: ReactNode;
  right?: ReactNode;
  backHref?: string;
  backLabel?: string;
}) {
  return (
    <div className="nr-hero-clip" style={{ position: "relative", marginBottom: 24 }}>
      <div aria-hidden style={{ position: "absolute", inset: "-28px -32px auto -32px", height: 190, background: "radial-gradient(560px 190px at 14% 0%, var(--glow1), transparent 72%)", pointerEvents: "none", zIndex: 0 }} />
      <div style={{ position: "relative", zIndex: 1 }}>
        {backHref && (
          <div style={{ marginBottom: 12 }}>
            <Link href={backHref} className="mono" style={{ fontSize: 12, color: "var(--muted)", textDecoration: "none" }}>← {backLabel}</Link>
          </div>
        )}
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
          <div style={{ minWidth: 0 }}>
            <span className="mono" style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: 10.5, letterSpacing: "0.12em", color: "var(--accent-soft-fg)", background: "var(--accent-soft)", border: "1px solid var(--accent-soft-bd)", padding: "4px 11px", borderRadius: 999, marginBottom: 13 }}>
              <span className="pulse-dot" /> {eyebrow}
            </span>
            <h1 className="serif" style={{ fontSize: "clamp(28px,5.4vw,38px)", fontWeight: 500, letterSpacing: "-0.02em", margin: "0 0 8px", lineHeight: 1.04 }}>{title}</h1>
            {subtitle && <p style={{ fontSize: 15, color: "var(--ink2)", margin: 0, maxWidth: "62ch", lineHeight: 1.5 }}>{subtitle}</p>}
          </div>
          {right && <div className="nr-hero-right" style={{ flexShrink: 0 }}>{right}</div>}
        </div>
      </div>
    </div>
  );
}
