import Link from "next/link";

/** The year-nav's one non-numeric stop (N8): every dated entry before the record's fixed start year,
 *  folded into a single "Earlier" tab rather than left unreachable. */
export const EARLIER_YEAR = "earlier" as const;

export interface EciYearCount {
  year: number | typeof EARLIER_YEAR;
  count: number;
}

function yearHref(year: number | typeof EARLIER_YEAR, preserve: Record<string, string | undefined>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(preserve)) if (v) p.set(k, v);
  p.set("year", String(year));
  return `/eci-files/entries?${p.toString()}`;
}

/** The year jump nav (REDESIGN brief: "real per-year counts") — every year's count reflects the current
 *  lane/status/topic/person filters, so the row stays honest as those change; only the year itself picks
 *  which slice of it renders below. */
export function EntriesYearNav({ years, activeYear, preserve }: { years: EciYearCount[]; activeYear: number | typeof EARLIER_YEAR; preserve: Record<string, string | undefined> }) {
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
            <span style={{ fontSize: 14, fontWeight: active ? 700 : 600 }}>{y.year === EARLIER_YEAR ? "Earlier" : y.year}</span>
            <span className="mono" style={{ fontSize: 10, opacity: active ? 0.85 : 1, color: active ? "inherit" : "var(--muted)" }}>{y.count}</span>
          </Link>
        );
      })}
    </div>
  );
}
