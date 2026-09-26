import type { EciAnswerRow, EciAnswersCounts } from "@/types/eci-files";

interface YearBucket {
  year: string;
  answered: number;
  unanswered: number;
  total: number;
}

function yearBuckets(rows: EciAnswerRow[]): YearBucket[] {
  const byYear = new Map<string, YearBucket>();
  for (const row of rows) {
    const year = row.charge.date ? row.charge.date.slice(0, 4) : "Undated";
    let b = byYear.get(year);
    if (!b) {
      b = { year, answered: 0, unanswered: 0, total: 0 };
      byYear.set(year, b);
    }
    b.total += 1;
    if (row.responses.length > 0) b.answered += 1;
    else b.unanswered += 1;
  }
  return [...byYear.values()].sort((a, b) => (a.year < b.year ? -1 : a.year > b.year ? 1 : 0));
}

const CHART_H = 108;

/** The answers page's one visual answer: the two big counts (answered / no response on record) beside a
 *  chart of how many charges the Commission answered, stacked by year. Built from the full, unfiltered
 *  row set, so the hero never moves when the filter chips below it do. Faithful to
 *  `docs/eci-files/designs/D-After-Answers.dc.html`. */
export function AnswersHero({ rows, counts }: { rows: EciAnswerRow[]; counts: EciAnswersCounts }) {
  const years = yearBuckets(rows);
  const max = Math.max(1, ...years.map((y) => y.total));

  return (
    <div className="eci2-card eci2-answers-hero">
      <div className="eci2-answers-hero-counts">
        <div className="mono eci2-eyebrow">{counts.rows} charges, 2019–2026</div>
        <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
          <span style={{ fontSize: 44, fontWeight: 700, lineHeight: 1, color: "var(--ink)" }}>{counts.with_response}</span>
          <span style={{ fontSize: 14.5, color: "var(--ink2)" }}>answered</span>
        </div>
        <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
          <span style={{ fontSize: 24, fontWeight: 650, lineHeight: 1, color: "var(--muted)" }}>{counts.without_response}</span>
          <span style={{ fontSize: 13, color: "var(--muted)" }}>no response on record</span>
        </div>
      </div>

      <div className="eci2-answers-hero-divider" aria-hidden="true" />

      <div className="eci2-answers-hero-chart">
        <span style={{ fontSize: 13, color: "var(--ink2)" }}>How many charges the Commission answered, by year</span>
        <div
          role="img"
          aria-label={`Charges by year: ${years.map((y) => `${y.year}, ${y.answered} of ${y.total} answered`).join("; ")}.`}
          style={{ display: "flex", alignItems: "flex-end", gap: "clamp(10px,2vw,32px)", height: CHART_H, overflowX: "auto" }}
        >
          {years.map((y) => {
            const answeredH = Math.round((y.answered / max) * CHART_H);
            const unansweredH = Math.round((y.unanswered / max) * CHART_H);
            return (
              <div key={y.year} className="eci2-year-col">
                <div className="eci2-year-bar" style={{ height: Math.max(answeredH + unansweredH, 2) }} aria-hidden="true">
                  {y.answered > 0 && <div className="eci2-year-bar-answered" style={{ height: answeredH }} />}
                  {y.unanswered > 0 && <div className="eci2-year-bar-unanswered" style={{ height: unansweredH }} />}
                </div>
                <span className="mono" style={{ fontSize: 12, color: "var(--ink2)" }}>{y.year}</span>
                <span className="mono" style={{ fontSize: 10.5, color: "var(--muted)" }}>{y.total}</span>
              </div>
            );
          })}
        </div>
        <div className="eci-legend">
          <span className="eci-legend-item">
            <span aria-hidden style={{ width: 12, height: 8, borderRadius: 2, background: "var(--eci-ink)", display: "inline-block" }} />
            Answered
          </span>
          <span className="eci-legend-item">
            <span aria-hidden style={{ width: 12, height: 8, borderRadius: 2, background: "var(--eci-seq-1)", border: "1px solid var(--eci-seq-2)", display: "inline-block" }} />
            No response on record
          </span>
        </div>
      </div>
    </div>
  );
}
