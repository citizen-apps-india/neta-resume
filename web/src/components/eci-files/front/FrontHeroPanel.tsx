import type { EciHeadlineStat } from "@/types/eci-files";
import { ECI_RECORD_START_MONTH, ECI_RECORD_END_MONTH, toMonthKey, type EciMonthTotal } from "@/lib/eci-files";

const OPACITY_STEPS = [0.32, 0.52, 0.74, 1];

function barOpacity(total: number, max: number): number {
  if (total <= 0 || max <= 0) return 0;
  const r = total / max;
  if (r > 0.75) return 1;
  if (r > 0.5) return 0.74;
  if (r > 0.25) return 0.52;
  return 0.32;
}

/** Every month a new year starts, for the strip's own year row (V6: the strip was the only thing in a
 *  tall right-hand column, so it earns real height and its own year ticks rather than sitting in mostly
 *  empty space). */
function yearTicks(months: EciMonthTotal[]): { i: number; year: string }[] {
  const out: { i: number; year: string }[] = [];
  let last = "";
  months.forEach((m, i) => {
    const year = m.month.slice(0, 4);
    if (year !== last) {
      out.push({ i, year });
      last = year;
    }
  });
  return out;
}

/** The front page's density strip: one hand-drawn bar per month, 2019 to today, no interaction — the
 *  lane timeline's `DensityStrip` is the click/drag-to-window version used there; this is the slim,
 *  static read of the same `/eci-files/density` shape. */
function MonthStrip({ months }: { months: EciMonthTotal[] }) {
  const max = Math.max(1, ...months.map((m) => m.total));
  const nowKey = toMonthKey(new Date());
  const ticks = yearTicks(months);
  const STEP = 8;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0, height: "100%", justifyContent: "center" }}>
      <span style={{ fontSize: 14, color: "var(--ink2)" }}>The record, month by month, {ECI_RECORD_START_MONTH.slice(0, 4)}–{ECI_RECORD_END_MONTH.slice(0, 4)}</span>
      <div style={{ overflowX: "auto", paddingBottom: 2 }}>
        <div style={{ position: "relative", minWidth: months.length * STEP, paddingBottom: 16 }}>
          <div style={{ display: "flex", alignItems: "flex-end", gap: 2, height: 48 }}>
            {months.map((m) => {
              const isNow = m.month === nowKey;
              const op = barOpacity(m.total, max);
              return (
                <span
                  key={m.month}
                  title={`${m.month} · ${m.total} ${m.total === 1 ? "entry" : "entries"}`}
                  style={{
                    width: 6, height: 44, borderRadius: 1, flexShrink: 0,
                    background: op > 0 ? "var(--eci-ink)" : "var(--rule)",
                    opacity: op > 0 ? op : 1,
                    boxShadow: isNow ? "0 0 0 2px var(--ink)" : "none",
                  }}
                />
              );
            })}
          </div>
          <div aria-hidden style={{ position: "relative", height: 14 }}>
            {ticks.map((t) => (
              <span
                key={t.year}
                className="mono"
                style={{ position: "absolute", left: t.i * STEP, top: 2, fontSize: 10, color: "var(--muted)" }}
              >
                {t.year}
              </span>
            ))}
          </div>
        </div>
      </div>
      <div className="mono" style={{ display: "flex", gap: 10, alignItems: "center", fontSize: 10.5, color: "var(--muted)", flexWrap: "wrap" }}>
        <span>fewer</span>
        {OPACITY_STEPS.map((o) => <span key={o} aria-hidden style={{ width: 14, height: 8, borderRadius: 1, background: "var(--eci-ink)", opacity: o }} />)}
        <span>more</span>
        <span style={{ marginLeft: 4, color: "var(--ink)" }}>↑ the boxed month is where this record stands today</span>
      </div>
    </div>
  );
}

/** The hero card: one number with its source, three secondary numbers, and the density strip beside them
 *  (REDESIGN brief: "one hero number with its source link, three secondary numbers, a slim month density
 *  strip"). `headline` is `/eci-files/summary`'s four curated stats — index 0 is the hero. */
export function FrontHeroPanel({ headline, months }: { headline: EciHeadlineStat[]; months: EciMonthTotal[] }) {
  if (headline.length === 0) return null;
  const [hero, ...secondary] = headline;
  return (
    <div style={{ background: "var(--card)", border: "1px solid var(--rule)", borderRadius: 14, padding: "24px clamp(16px,4vw,32px)" }}>
      <div className="eci-front-hero-grid">
        <div style={{ display: "flex", flexDirection: "column", gap: 16, minWidth: 0 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <span className="mono" style={{ fontSize: "clamp(32px,6vw,52px)", fontWeight: 500, lineHeight: 1, color: "var(--ink)" }}>{hero.value}</span>
            <span style={{ fontSize: 14.5, color: "var(--ink2)" }}>{hero.label}</span>
            <a
              href={hero.source_url} target="_blank" rel="noopener noreferrer" className="mono"
              style={{ fontSize: 11, color: "var(--muted)", textDecoration: "none" }}
            >
              → {hero.source_label}
            </a>
          </div>
          {secondary.length > 0 && (
            <div style={{ display: "flex", gap: 28, flexWrap: "wrap", paddingTop: 8, borderTop: "1px solid var(--rule2)" }}>
              {secondary.map((s) => (
                <div key={s.entry_id + s.label} style={{ display: "flex", flexDirection: "column", gap: 3, minWidth: 0, maxWidth: 180 }}>
                  <span className="mono" style={{ fontSize: 24, fontWeight: 500, color: "var(--ink)" }}>{s.value}</span>
                  <span style={{ fontSize: 11.5, color: "var(--muted)", lineHeight: 1.3 }}>{s.label}</span>
                  <a
                    href={s.source_url} target="_blank" rel="noopener noreferrer" className="mono"
                    style={{ fontSize: 10, color: "var(--muted)", textDecoration: "none" }}
                  >
                    → {s.source_label}
                  </a>
                </div>
              ))}
            </div>
          )}
        </div>
        <MonthStrip months={months} />
      </div>
    </div>
  );
}
