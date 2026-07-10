import type { ReactNode } from "react";
import Link from "next/link";

/** Card wrapper with an optional header (serif title + mono source tag + a "see all →" action). Replaces the
 *  repeated inline cardStyle/headStyle across the Parliament pages. Token-only server component. */
export function SectionCard({
  title, source, action, actionHref, children, className = "", pad = true,
}: {
  title?: ReactNode;
  source?: ReactNode;
  action?: string;
  actionHref?: string;
  children: ReactNode;
  className?: string;
  pad?: boolean;
}) {
  return (
    <section
      className={className}
      style={{ border: "1px solid var(--rule)", borderRadius: 14, background: "var(--card2)", padding: pad ? "clamp(16px,3vw,22px)" : 0, minWidth: 0, display: "flex", flexDirection: "column" }}
    >
      {(title || (action && actionHref)) && (
        <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, marginBottom: 14 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 10, minWidth: 0 }}>
            {title && <span className="serif" style={{ fontSize: 15.5, fontWeight: 600 }}>{title}</span>}
            {source && <span className="mono" style={{ fontSize: 9.5, color: "var(--faint)", letterSpacing: "0.06em", whiteSpace: "nowrap" }}>{source}</span>}
          </div>
          {action && actionHref && (
            <Link href={actionHref} className="mono" style={{ fontSize: 11.5, color: "var(--accent-2)", textDecoration: "none", whiteSpace: "nowrap" }}>{action}</Link>
          )}
        </div>
      )}
      {children}
    </section>
  );
}
