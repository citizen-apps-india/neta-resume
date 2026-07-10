import Link from "next/link";
import { themeColor } from "@/lib/themes";
import type { MinistryCount } from "@/lib/api";

/** Ranked ministries as theme-coloured proportional bars. Each row links to the themed directory so a
 *  reader can jump from "what's asked about" to "who asks about it". Server-rendered. */
export function MinistryBars({ items }: { items: MinistryCount[] }) {
  const max = Math.max(...items.map((m) => m.count), 1);
  return (
    <div style={{ display: "grid", gap: 4 }}>
      {items.map((m) => (
        <Link
          key={`${m.ministry}·${m.theme}`}
          href={`/directory?theme=${encodeURIComponent(m.theme)}&sort=theme_questions`}
          className="tap"
          title={`${m.theme} — explore MPs who raise this`}
          style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: "4px 12px", alignItems: "baseline", textDecoration: "none", color: "var(--ink)", padding: "6px 8px", borderRadius: 8 }}
        >
          <span style={{ fontSize: 13.5, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{m.ministry}</span>
          <span className="mono" style={{ fontSize: 12.5, fontWeight: 600, color: "var(--ink2)" }}>{m.count.toLocaleString("en-IN")}</span>
          <div style={{ gridColumn: "1 / -1", height: 8, background: "var(--sunken)", borderRadius: 5, overflow: "hidden" }}>
            <div style={{ width: `${(m.count / max) * 100}%`, height: "100%", background: themeColor(m.theme), borderRadius: 5 }} />
          </div>
        </Link>
      ))}
    </div>
  );
}
