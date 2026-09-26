import type { EciCitation } from "@/types/eci-files";

/** Exported for the numbers pages' source lines (PHASE3-SPEC.md §3.6: "reuses the TIER_LABEL wording"). */
export const TIER_LABEL: Record<number, string> = { 1: "TIER 1 · PRIMARY", 2: "TIER 2 · RESEARCH/FILING", 3: "TIER 3 · PRESS" };

/** One citation row: publisher, tier, and the link — the "sourced" half of a sourced record. */
function Citation({ c }: { c: EciCitation }) {
  return (
    <li style={{ display: "flex", flexWrap: "wrap", alignItems: "baseline", gap: 8, padding: "6px 0" }}>
      <span
        className="mono"
        style={{ fontSize: 9, letterSpacing: "0.04em", color: "var(--faint)", border: "1px solid var(--border2)", borderRadius: 5, padding: "2px 6px", whiteSpace: "nowrap" }}
      >
        {TIER_LABEL[c.tier] ?? `TIER ${c.tier}`}
      </span>
      <a href={c.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 12.5, color: "var(--accent-2)", textDecoration: "none" }}>
        {c.title || c.publisher || c.url}
      </a>
      {c.publisher && <span style={{ fontSize: 11.5, color: "var(--muted)" }}>{c.publisher}</span>}
      {c.published && <span className="mono" style={{ fontSize: 11, color: "var(--faint)" }}>{c.published}</span>}
      {c.archive_url && (
        <a href={c.archive_url} target="_blank" rel="noopener noreferrer" className="mono" style={{ fontSize: 10.5, color: "var(--faint)", textDecoration: "none" }}>
          archived ↗
        </a>
      )}
      {c.quote && <span style={{ fontSize: 11.5, color: "var(--ink2)", fontStyle: "italic" }}>&ldquo;{c.quote}&rdquo;</span>}
    </li>
  );
}

/** Citations, in position order, each carrying its trust tier — the record wears its sources. */
export function CitationList({ citations }: { citations: EciCitation[] }) {
  if (citations.length === 0) {
    return <p style={{ fontSize: 11.5, color: "var(--muted)" }}>No citation on record — see gaps.</p>;
  }
  const sorted = [...citations].sort((a, b) => a.position - b.position);
  return (
    <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column" }}>
      {sorted.map((c) => (
        <Citation key={c.position} c={c} />
      ))}
    </ul>
  );
}
