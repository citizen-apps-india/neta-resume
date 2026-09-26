import Link from "next/link";
import type { CSSProperties } from "react";
import type { EciAnswerRow as EciAnswerRowT } from "@/types/eci-files";
import { eciEntryHrefIn, formatEciDate } from "@/lib/eci-files";
import { StatusChip } from "@/components/eci-files/StatusChip";
import { EntryRefLink } from "@/components/eci-files/views/EntryRefLink";
import { PendingFlag } from "@/components/ui";

const BASE_PATH = "/eci-files/answers";

function clamp(lines: number): CSSProperties {
  return { display: "-webkit-box", WebkitBoxOrient: "vertical", WebkitLineClamp: lines, overflow: "hidden" };
}

/** One row of the charge-and-answer ledger (PHASE5-SPEC §6.3): what was said or done, the response(s),
 *  and — only when a primary document bears directly on the point — what the record shows. Equal visual
 *  weight for charge and answer; the "record" column stays visually blank rather than showing a dash when
 *  there's nothing to put there (a dash would read as a gap, not as "not applicable"). */
export function AnswerRow({ row, preserve }: { row: EciAnswerRowT; preserve?: Record<string, string | undefined> }) {
  const { charge } = row;
  return (
    <article id={`charge-${charge.id}`} aria-labelledby={`charge-${charge.id}-h`} className="eci-answer-row">
      <div>
        <div className="eci-cell-label mono" style={{ fontSize: 10, letterSpacing: "0.05em", color: "var(--faint)", marginBottom: 4 }}>
          WHAT WAS SAID OR DONE
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 4 }}>
          <span className="mono" style={{ fontSize: 10.5, color: "var(--muted)" }}>{formatEciDate(charge.date, charge.date_precision)}</span>
          <StatusChip status={charge.status} />
          {charge.check_status === "unchecked" && <PendingFlag>NOT YET CHECKED</PendingFlag>}
        </div>
        {charge.attributed_to && (
          <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--ink)", marginBottom: 2 }}>{charge.attributed_to}</div>
        )}
        <h3 id={`charge-${charge.id}-h`} className="serif" style={{ fontSize: 15.5, fontWeight: 600, lineHeight: 1.35, margin: "0 0 6px" }}>
          <Link href={eciEntryHrefIn(BASE_PATH, charge.id, preserve)} style={{ color: "inherit", textDecoration: "none" }}>{charge.title}</Link>
        </h3>
        <p style={{ fontSize: 13, color: "var(--ink2)", lineHeight: 1.55, margin: "0 0 6px", ...clamp(4) }}>{charge.summary}</p>
        <Link href={eciEntryHrefIn(BASE_PATH, charge.id, preserve)} className="mono" style={{ fontSize: 11, color: "var(--accent-2)", textDecoration: "none" }}>
          Read in full
        </Link>
        {row.also_recorded_as.length > 0 && (
          <div style={{ marginTop: 8, fontSize: 12, color: "var(--muted)" }}>
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

      <div>
        <div className="eci-cell-label mono" style={{ fontSize: 10, letterSpacing: "0.05em", color: "var(--faint)", marginBottom: 4 }}>
          THE RESPONSE
        </div>
        {row.responses.length === 0 ? (
          <p style={{ fontSize: 13, color: "var(--muted)", margin: 0 }}>No response on record.</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {row.responses.map((r) => (
              <div key={r.id}>
                <div style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}>
                  <span className="mono" style={{ fontSize: 10.5, color: "var(--muted)" }}>{formatEciDate(r.date, r.date_precision)}</span>
                  {r.attributed_to && <strong style={{ fontSize: 12.5, color: "var(--ink)", fontWeight: 600 }}>{r.attributed_to}</strong>}
                </div>
                <Link href={eciEntryHrefIn(BASE_PATH, r.id, preserve)} className="serif" style={{ display: "block", fontSize: 14, fontWeight: 600, color: "var(--ink)", textDecoration: "none", margin: "2px 0 3px" }}>
                  {r.title}
                </Link>
                <p style={{ fontSize: 12.5, color: "var(--ink2)", lineHeight: 1.5, margin: 0, ...clamp(3) }}>{r.summary}</p>
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

      <div className={row.record.length === 0 ? "eci-cell-empty" : undefined}>
        {row.record.length > 0 && (
          <>
            <div className="eci-cell-label mono" style={{ fontSize: 10, letterSpacing: "0.05em", color: "var(--faint)", marginBottom: 4 }}>
              WHAT THE RECORD SHOWS
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {row.record.map((r) => (
                <div key={r.id}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 2 }}>
                    <StatusChip status={r.status} />
                    <span className="mono" style={{ fontSize: 10.5, color: "var(--muted)" }}>{formatEciDate(r.date, r.date_precision)}</span>
                  </div>
                  <Link href={eciEntryHrefIn(BASE_PATH, r.id, preserve)} style={{ fontSize: 12.5, color: "var(--eci-ink)", textDecoration: "none" }}>
                    {r.title}
                  </Link>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      {row.note && (
        <div style={{ gridColumn: "1 / -1" }}>
          <span className="mono" style={{ fontSize: 10, letterSpacing: "0.05em", color: "var(--ink2)" }}>NOTE </span>
          <span style={{ fontSize: 12.5, color: "var(--ink2)", fontStyle: "italic" }}>{row.note}</span>
        </div>
      )}
    </article>
  );
}
