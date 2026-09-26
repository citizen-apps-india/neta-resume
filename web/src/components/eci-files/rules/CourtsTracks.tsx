import Link from "next/link";
import type { EciCaseSummary } from "@/types/eci-files";
import { ECI_CASE_STATUS_LABEL, ECI_RECORD_END_MONTH, dateFraction, formatEciDate } from "@/lib/eci-files";

const AXIS_START = "2019-01-01";
const AXIS_END = `${ECI_RECORD_END_MONTH}-01`;

/** The single visual answer on `/eci-files/courts`: every case as a horizontal track on one shared time
 *  axis, filed to its latest recorded step, with an end-cap that says how it stands — a shape, not only
 *  a colour, so "decided" / "pending" / "referred" survive colour-blindness and greyscale printing alike. */
export function CourtsTracks({ cases }: { cases: EciCaseSummary[] }) {
  const dates = cases.flatMap((c) => [c.first_date, c.last_date]).filter((d): d is string => !!d);
  const from = dates.length > 0 ? dates.reduce((a, b) => (b < a ? b : a), AXIS_START) : AXIS_START;
  const to = dates.length > 0 ? dates.reduce((a, b) => (b > a ? b : a), AXIS_END) : AXIS_END;
  const years: string[] = [];
  for (let y = Number(from.slice(0, 4)); y <= Number(to.slice(0, 4)); y++) years.push(String(y));

  return (
    <div>
      <div className="eci-legend" style={{ marginBottom: 12 }}>
        <span className="eci-legend-item"><span aria-hidden className="eci-track-legend-dot" />Decided</span>
        <span className="eci-legend-item"><span aria-hidden className="eci-track-legend-dash" />Pending</span>
        <span className="eci-legend-item"><span aria-hidden className="eci-track-legend-diamond" />Referred</span>
      </div>
      <div className="eci-tracks">
        <div className="eci-tracks-scroll">
          <div className="eci-tracks-inner">
            {cases.map((c) => {
              const x0 = c.first_date ? dateFraction(c.first_date, from, to) : 0;
              const x1raw = c.last_date ? dateFraction(c.last_date, from, to) : x0;
              const x1 = Math.max(x0, x1raw);
              const label = `${c.short_name}: ${ECI_CASE_STATUS_LABEL[c.short_status]}, ${c.item_count} recorded step${c.item_count === 1 ? "" : "s"}, latest ${
                c.latest ? `${formatEciDate(c.latest.date, c.latest.date_precision)} — ${c.latest.title}` : "not recorded"
              }`;
              return (
                <Link key={c.slug} href={`/eci-files/courts/${c.slug}`} className="eci-track-row" aria-label={label}>
                  <div className="eci-track-meta">
                    <span className="serif eci-track-name">{c.short_name}</span>
                    <span className="mono eci-track-sub">
                      {c.item_count} step{c.item_count === 1 ? "" : "s"} · {c.order_count} order{c.order_count === 1 ? "" : "s"} ·{" "}
                      <span
                        className="mono"
                        style={{
                          display: "inline-block", padding: "2px 7px", borderRadius: 999, fontSize: 10,
                          border: "1px solid var(--border2)", background: "var(--sunken)", color: "var(--ink2)",
                        }}
                      >
                        {ECI_CASE_STATUS_LABEL[c.short_status]}
                      </span>
                    </span>
                  </div>
                  <div className="eci-track-line-wrap" aria-hidden>
                    <span className="eci-track-base" style={{ left: `${x0 * 100}%`, width: `${Math.max(0.4, (x1 - x0) * 100)}%` }} />
                    <span className="eci-track-start" style={{ left: `${x0 * 100}%` }} />
                    {c.short_status === "disposed" && <span className="eci-track-end-decided" style={{ left: `${x1 * 100}%` }} />}
                    {c.short_status === "referred" && <span className="eci-track-end-referred" style={{ left: `${x1 * 100}%` }} />}
                    {c.short_status === "pending" && (
                      <>
                        <span className="eci-track-dash" style={{ left: `${x1 * 100}%`, right: 0 }} />
                        <span className="eci-track-end-pending" style={{ left: "100%" }} />
                      </>
                    )}
                  </div>
                </Link>
              );
            })}
            <div className="eci-tracks-ticks">
              {years.map((y) => (
                <span key={y} className="mono" style={{ left: `${dateFraction(`${y}-01-01`, from, to) * 100}%` }}>{y}</span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
