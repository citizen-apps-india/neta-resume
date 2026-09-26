import type { EciCitation } from "@/types/eci-files";
import type { EciCareerItem } from "@/lib/eci-files";
import { CareerTimeline } from "@/components/eci-files/CareerTimeline";
import { CitationList } from "@/components/eci-files/CitationList";

/** "Full career · education, all N postings and sources ↓" (C-After-Profile.dc.html): the complete
 *  career — including undated postings and every source — and the profile's citations, folded behind one
 *  disclosure so the hero card's horizontal line can stay short. Native `<details>`, no client JS. */
export function FullCareerDisclosure({
  education, dated, undated, citations,
}: {
  education: string | null;
  dated: EciCareerItem[];
  undated: EciCareerItem[];
  citations: EciCitation[];
}) {
  const postingCount = dated.length + undated.length;
  if (postingCount === 0 && citations.length === 0) return null;

  return (
    <details className="eci-more">
      <summary
        className="mono"
        style={{
          display: "inline-flex", alignSelf: "flex-start", minHeight: 40, alignItems: "center", padding: "0 18px", borderRadius: 12,
          border: "1px dashed var(--border2)", fontSize: 13, color: "var(--ink2)", cursor: "pointer", listStyle: "none",
        }}
      >
        Full career{education ? " · education" : ""}{postingCount > 0 ? `, all ${postingCount} posting${postingCount === 1 ? "" : "s"}` : ""} and sources ↓
      </summary>
      <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 24 }}>
        {postingCount > 0 && (
          <div>
            {education && <p style={{ fontSize: 12.5, color: "var(--muted)", margin: "0 0 12px" }}>Education: {education}</p>}
            <CareerTimeline dated={dated} undated={undated} />
          </div>
        )}
        {citations.length > 0 && (
          <div>
            <h3 className="serif" style={{ fontSize: 15, fontWeight: 600, margin: "0 0 8px" }}>
              Sources for this profile <span className="mono" style={{ fontSize: 11.5, color: "var(--faint)", fontWeight: 400 }}>{citations.length}</span>
            </h3>
            <CitationList citations={citations} />
          </div>
        )}
      </div>
    </details>
  );
}
