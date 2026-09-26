import Link from "next/link";

export interface EciYearCount {
  year: number;
  count: number;
}

function yearHref(year: number, preserve: Record<string, string | undefined>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(preserve)) if (v) p.set(k, v);
  p.set("year", String(year));
  return `/eci-files/entries?${p.toString()}`;
}

/** The year jump nav (REDESIGN brief: "real per-year counts") — every year's count reflects the current
 *  lane/status/topic/person filters, so the row stays honest as those change; only the year itself picks
 *  which slice of it renders below. */
export function EntriesYearNav({ years, activeYear, preserve }: { years: EciYearCount[]; activeYear: number; preserve: Record<string, string | undefined> }) {
  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
      {years.map((y) => {
        const active = y.year === activeYear;
        return (
          <Link
            key={y.year}
            href={yearHref(y.year, preserve)}
            scroll={false}
            aria-current={active ? "true" : undefined}
            className="tap"
            style={{
              display: "inline-flex", flexDirection: "column", alignItems: "center", gap: 1,
              padding: "6px 14px", borderRadius: 10, minHeight: 40, textDecoration: "none",
              border: `1px solid ${active ? "var(--eci-ink)" : "var(--border)"}`,
              background: active ? "var(--eci-ink)" : "var(--card2)",
              color: active ? "#fff" : "var(--ink)",
            }}
          >
            <span style={{ fontSize: 14, fontWeight: active ? 700 : 600 }}>{y.year}</span>
            <span className="mono" style={{ fontSize: 10, opacity: active ? 0.85 : 1, color: active ? "inherit" : "var(--muted)" }}>{y.count}</span>
          </Link>
        );
      })}
    </div>
  );
}
