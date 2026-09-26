import Link from "next/link";
import type { CSSProperties } from "react";
import type { EciAnswerRow as EciAnswerRowT } from "@/types/eci-files";
import { eciEntryHref, formatEciDate } from "@/lib/eci-files";
import { StatusWord } from "@/components/eci-files/ui/StatusWord";
import { EntryRefLink } from "@/components/eci-files/views/EntryRefLink";
import { LinkifiedNote } from "@/components/eci-files/views/LinkifiedNote";

const BASE_PATH = "/eci-files/answers";

function clamp(lines: number): CSSProperties {
  return { display: "-webkit-box", WebkitBoxOrient: "vertical", WebkitLineClamp: lines, overflow: "hidden" };
}

/** One charge-and-answer row: the charge and its reply as two strictly equal-weight columns — same
 *  heading size, same body size, "No response on record." set at the same weight as a real reply's title
 *  rather than shrunk into a footnote. "What the record shows" is a thin marker under the pair, present
 *  only when a documented entry bears directly on the point (never a blank third column). Faithful to
 *  `docs/eci-files/designs/D-After-Answers.dc.html`. */
export function ChargeAnswerRow({ row, preserve }: { row: EciAnswerRowT; preserve?: Record<string, string | undefined> }) {
  const { charge } = row;
  return (
    <article id={`charge-${charge.id}`} aria-labelledby={`charge-${charge.id}-h`} className="eci2-answer-row">
      <div className="eci2-answer-col">
        <div className="mono eci2-cell-label">What was said or done</div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", marginBottom: 6 }}>
          <span className="mono" style={{ fontSize: 12, color: "var(--muted)" }}>{formatEciDate(charge.date, charge.date_precision)}</span>
          <StatusWord status={charge.status} checked={charge.check_status === "checked"} />
        </div>
        {charge.attributed_to && (
          <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--ink2)", marginBottom: 2 }}>{charge.attributed_to}</div>
        )}
        <h3 id={`charge-${charge.id}-h`} className="eci2-answer-title">
          <Link href={eciEntryHref(charge.id, preserve, BASE_PATH)} style={{ color: "inherit", textDecoration: "none" }}>{charge.title}</Link>
        </h3>
        <p style={{ fontSize: 13.5, color: "var(--ink2)", lineHeight: 1.55, margin: "0 0 6px", ...clamp(3) }}>{charge.summary}</p>
        {row.also_recorded_as.length > 0 && (
          <div style={{ marginTop: 6, fontSize: 12, color: "var(--muted)" }}>
            Also recorded as:{" "}
            {row.also_recorded_as.map((e, i) => (
              <span key={e.id}>
                {i > 0 && ", "}
                <EntryRefLink entry={e} basePath={BASE_PATH} preserve={preserve} />
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="eci2-answer-col">
        <div className="mono eci2-cell-label">The reply</div>
        {row.responses.length === 0 ? (
          <p className="eci2-answer-title" style={{ color: "var(--muted)" }}>No response on record.</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {row.responses.map((r) => (
              <div key={r.id}>
                <div style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap", marginBottom: 2 }}>
                  <span className="mono" style={{ fontSize: 12, color: "var(--muted)" }}>{formatEciDate(r.date, r.date_precision)}</span>
                  {r.attributed_to && <strong style={{ fontSize: 12.5, color: "var(--ink2)", fontWeight: 600 }}>{r.attributed_to}</strong>}
                </div>
                <h3 className="eci2-answer-title">
                  <Link href={eciEntryHref(r.id, preserve, BASE_PATH)} style={{ color: "inherit", textDecoration: "none" }}>{r.title}</Link>
                </h3>
                <p style={{ fontSize: 13.5, color: "var(--ink2)", lineHeight: 1.55, margin: 0, ...clamp(3) }}>{r.summary}</p>
              </div>
            ))}
          </div>
        )}
        {row.related.length > 0 && (
          <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
            {row.related.map((rel) => (
              <div key={rel.entry.id} style={{ fontSize: 12, color: "var(--muted)" }}>
                {rel.why}: <EntryRefLink entry={rel.entry} basePath={BASE_PATH} preserve={preserve} />
              </div>
            ))}
          </div>
        )}
      </div>

      {row.record.length > 0 && (
        <div className="eci2-answer-record">
          <span className="mono eci2-answer-record-label">Record</span>
          <div className="eci2-answer-record-list">
            {row.record.map((r) => (
              <span key={r.id} className="eci2-answer-record-item">
                <Link href={eciEntryHref(r.id, preserve, BASE_PATH)} style={{ color: "inherit", textDecoration: "none" }}>{r.title}</Link>
                <span className="mono" style={{ color: "var(--muted)", marginLeft: 8 }}>{formatEciDate(r.date, r.date_precision)}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {row.note && (
        <div className="eci2-answer-note">
          <span className="mono" style={{ fontSize: 10, letterSpacing: "0.05em", color: "var(--ink2)" }}>NOTE </span>
          <span style={{ fontSize: 12.5, color: "var(--ink2)", fontStyle: "italic" }}><LinkifiedNote text={row.note} basePath={BASE_PATH} /></span>
        </div>
      )}
    </article>
  );
}
