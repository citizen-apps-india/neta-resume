import type { EciSummaryCounts } from "@/types/eci-files";
import { formatLooseDate } from "@/lib/eci-files";

/** "About this record", collapsed by default (REDESIGN brief: long text goes behind a "Details"/"Read
 *  more" control) — the record-wide counts sit next to it either way, since those are a glance, not prose. */
export function FrontAbout({ counts, lastLoaded }: { counts: EciSummaryCounts; lastLoaded: string | null }) {
  return (
    <div style={{ display: "flex", alignItems: "flex-start", gap: 16, flexWrap: "wrap", paddingTop: 8, borderTop: "1px solid var(--rule)" }}>
      <details className="eci-front-about">
        <summary className="mono tap">
          About this record
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
            <path d="M3 4.5l3 3 3-3" stroke="var(--muted)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </summary>
        <p style={{ fontSize: 13.5, color: "var(--ink2)", lineHeight: 1.6, maxWidth: "68ch", margin: "10px 0 0" }}>
          A dated record of the Election Commission of India, 2019 to today — documents, reports and named
          claims, kept apart and each one linked to where it comes from. Every entry is labelled by how well
          it is sourced, and anything a fact-checker hasn&apos;t opened yet is marked &ldquo;not yet
          checked&rdquo; rather than presented as settled.
          {lastLoaded && <> Last loaded {formatLooseDate(lastLoaded)}.</>}
        </p>
      </details>
      <span className="mono" style={{ fontSize: 12, color: "var(--muted)", paddingTop: 8 }}>
        {counts.entries.toLocaleString("en-IN")} entries · {counts.checked.toLocaleString("en-IN")} checked ·{" "}
        {counts.people.toLocaleString("en-IN")} people named · {counts.citations.toLocaleString("en-IN")} citations
      </span>
    </div>
  );
}
