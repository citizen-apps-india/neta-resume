import type { EciCareerItem } from "@/lib/eci-files";
import { dateFraction } from "@/lib/eci-files";

const TIER_HEIGHT = 34;
const BAR_TOP = 0;
const BAR_HEIGHT = 8;
const TIER_COUNT = 3;

function axisFromItems(dated: EciCareerItem[]): { from: string; to: string } {
  const first = dated[0];
  const today = new Date().toISOString().slice(0, 10);
  return { from: first.from ?? first.to ?? today, to: today };
}

function geometry(item: EciCareerItem, isLast: boolean, axis: { from: string; to: string }): { x0: number; width: number } {
  const start = item.from ?? item.to ?? axis.from;
  const x0 = dateFraction(start, axis.from, axis.to);
  const x1 = item.to ? dateFraction(item.to, axis.from, axis.to) : isLast ? 1 : x0;
  return { x0, width: Math.max(0.014, x1 - x0) };
}

function UndatedTags({ undated }: { undated: EciCareerItem[] }) {
  if (undated.length === 0) return null;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
      <span style={{ fontSize: 11, color: "var(--faint)" }}>Also held, undated:</span>
      {undated.map((item, i) => (
        <span
          key={i}
          style={{ fontSize: 11.5, color: "var(--muted)", background: "var(--bg)", border: "1px solid var(--rule)", borderRadius: 999, padding: "4px 10px" }}
        >
          {item.post}
        </span>
      ))}
    </div>
  );
}

/** Identity's "one horizontal career line on a time axis" (C-After-Profile.dc.html, C-Phone-Profile.dc.html):
 *  postings proportional to their real dates, ECI roles highlighted in the section accent, undated
 *  postings folded into tags below rather than dated arbitrarily. Renders both a desktop (proportional
 *  axis, labels staggered across three tiers so consecutive short postings don't collide) and a phone
 *  variant (a plain stacked list, same order) — CSS toggles which one shows, the pattern
 *  `ProfileHeader`'s `.eci-avatar-lg`/`.eci-avatar-sm` already uses. */
export function CareerLine({ dated, undated }: { dated: EciCareerItem[]; undated: EciCareerItem[] }) {
  if (dated.length === 0 && undated.length === 0) return null;

  const axis = dated.length > 0 ? axisFromItems(dated) : null;
  const maxTier = dated.length > 0 ? Math.min(dated.length, TIER_COUNT) - 1 : 0;
  const chartHeight = BAR_TOP + BAR_HEIGHT + 14 + (maxTier + 1) * TIER_HEIGHT;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {axis && (
        <div className="eci-careerline-desktop" style={{ overflowX: "auto" }}>
          <div style={{ position: "relative", minWidth: 560, height: chartHeight }}>
            <div aria-hidden style={{ position: "absolute", left: 0, right: 0, top: BAR_TOP + BAR_HEIGHT / 2, borderTop: "1px solid var(--rule2)" }} />
            {dated.map((item, i) => {
              const isLast = i === dated.length - 1;
              const { x0, width } = geometry(item, isLast, axis);
              const tier = i % TIER_COUNT;
              const labelTop = BAR_TOP + BAR_HEIGHT + 8 + tier * TIER_HEIGHT;
              return (
                <div key={i}>
                  <span
                    aria-hidden
                    style={{
                      position: "absolute", left: `${x0 * 100}%`, top: BAR_TOP, width: `${width * 100}%`, height: BAR_HEIGHT,
                      borderRadius: 4, background: item.atCommission ? "var(--eci-ink)" : "var(--border2)",
                    }}
                  />
                  <span
                    aria-hidden
                    style={{ position: "absolute", left: `${x0 * 100}%`, top: BAR_TOP + BAR_HEIGHT, width: 0, height: labelTop - (BAR_TOP + BAR_HEIGHT), borderLeft: "1px solid var(--rule2)" }}
                  />
                  <div style={{ position: "absolute", left: `${x0 * 100}%`, top: labelTop, width: 190, display: "flex", flexDirection: "column", gap: 0 }}>
                    <span className="mono" style={{ fontSize: 10, color: "var(--muted)" }}>{item.label}</span>
                    <span style={{ fontSize: 12, fontWeight: 600, color: item.atCommission ? "var(--eci-ink)" : "var(--ink)", lineHeight: 1.25 }}>
                      {item.post}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {dated.length > 0 && (
        <ol className="eci-careerline-mobile" style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 6 }}>
          {dated.map((item, i) => (
            <li key={i} style={{ display: "flex", gap: 8, alignItems: "baseline" }}>
              <span className="mono" style={{ fontSize: 9.5, color: "var(--muted)", width: 70, flexShrink: 0 }}>{item.label}</span>
              <span style={{ fontSize: 12, fontWeight: item.atCommission ? 700 : 500, color: item.atCommission ? "var(--eci-ink)" : "var(--ink)" }}>
                {item.post}
              </span>
            </li>
          ))}
        </ol>
      )}

      <UndatedTags undated={undated} />
    </div>
  );
}
