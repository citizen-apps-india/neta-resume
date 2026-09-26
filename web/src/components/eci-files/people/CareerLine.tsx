import type { EciCareerItem } from "@/lib/eci-files";
import { dateFraction } from "@/lib/eci-files";

const BAR_HEIGHT = 8;

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

function yearTicks(axis: { from: string; to: string }): number[] {
  const y0 = Number(axis.from.slice(0, 4)) + 1;
  const y1 = Number(axis.to.slice(0, 4));
  const span = y1 - y0;
  const step = span > 24 ? 5 : span > 12 ? 3 : span > 6 ? 2 : 1;
  const out: number[] = [];
  for (let y = y0; y <= y1; y += step) out.push(y);
  return out;
}

/** The career as one proportional bar (ECI roles in the section accent) with a numbered marker per posting,
 *  and the postings as a numbered list beneath it. The bar carries no text of its own, so long posting
 *  names can never collide; the list is the readable part and the bar's legend. Phones get the list alone. */
export function CareerLine({ dated, undated }: { dated: EciCareerItem[]; undated: EciCareerItem[] }) {
  if (dated.length === 0 && undated.length === 0) return null;
  const axis = dated.length > 0 ? axisFromItems(dated) : null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {axis && (
        <div className="eci-careerline-bar" aria-hidden style={{ position: "relative", height: 52 }}>
          <div style={{ position: "absolute", left: 0, right: 0, top: 22, borderTop: "1px solid var(--rule2)" }} />
          {dated.map((item, i) => {
            const { x0, width } = geometry(item, i === dated.length - 1, axis);
            const accent = item.atCommission ? "var(--eci-ink)" : "var(--border2)";
            return (
              <div key={i}>
                <span style={{ position: "absolute", left: `${x0 * 100}%`, top: 18, width: `calc(${width * 100}% - 2px)`, height: BAR_HEIGHT, borderRadius: 4, background: accent }} />
                <span
                  className="mono"
                  style={{
                    position: "absolute", left: `${x0 * 100}%`, top: 0, transform: "translateX(-2px)", fontSize: 10, fontWeight: 600,
                    color: item.atCommission ? "var(--eci-ink)" : "var(--muted)",
                  }}
                >
                  {i + 1}
                </span>
              </div>
            );
          })}
          {yearTicks(axis).map((y) => (
            <span key={y} className="mono" style={{ position: "absolute", left: `${dateFraction(`${y}-01-01`, axis.from, axis.to) * 100}%`, top: 34, fontSize: 10, color: "var(--faint)", transform: "translateX(-50%)" }}>
              {y}
            </span>
          ))}
        </div>
      )}

      {dated.length > 0 && (
        <ol style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 8 }}>
          {dated.map((item, i) => (
            <li key={i} style={{ display: "grid", gridTemplateColumns: "22px 108px minmax(0, 1fr)", gap: 10, alignItems: "baseline" }}>
              <span className="mono" style={{ fontSize: 10.5, fontWeight: 600, color: item.atCommission ? "var(--eci-ink)" : "var(--muted)" }}>{i + 1}</span>
              <span className="mono" style={{ fontSize: 10.5, color: "var(--muted)" }}>{item.label}</span>
              <span style={{ fontSize: 13.5, lineHeight: 1.4, fontWeight: item.atCommission ? 650 : 500, color: item.atCommission ? "var(--eci-ink)" : "var(--ink)" }}>
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
