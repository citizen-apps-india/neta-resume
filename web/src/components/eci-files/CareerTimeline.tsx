import type { EciCareerItem } from "@/lib/eci-files";

function SourceChip({ source }: { source: EciCareerItem["sources"][number] }) {
  const label = source.kind === "official" ? "Official record" : source.kind === "court" ? "Court record" : "Press report";
  return (
    <a
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      className="mono"
      style={{
        display: "inline-flex", alignItems: "center", gap: 4, fontSize: 10.5, color: "var(--accent-2)",
        textDecoration: "none", border: "1px solid var(--rule)", borderRadius: 6, padding: "2px 8px", marginRight: 6,
      }}
    >
      {source.host} ↗ {label}
    </a>
  );
}

function CareerRow({ item, showDate = true }: { item: EciCareerItem; showDate?: boolean }) {
  return (
    <li className="eci-career-item" data-commission={item.atCommission ? "true" : undefined}>
      <div className="eci-career-row">
        {showDate && (
          <div className="eci-career-date mono" style={{ fontSize: 11.5, color: "var(--muted)", fontVariantNumeric: "tabular-nums" }}>
            {item.label}
          </div>
        )}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13.5, color: "var(--ink)", lineHeight: 1.5 }}>{item.post}</div>
          {item.sources.length > 0 && (
            <div style={{ marginTop: 4 }}>
              {item.sources.map((s, i) => <SourceChip key={i} source={s} />)}
            </div>
          )}
        </div>
      </div>
    </li>
  );
}

/** The career section on a profile (PHASE4-SPEC.md §2.4): dated postings oldest-first with a rail that
 *  colours "at the Commission" segments in ink, then undated postings in the source's own order. Data
 *  comes from `careerTimeline()` in `lib/eci-files.ts`, which replaced the old scalar `detailLines()` dump
 *  precisely so a personal detail like `born` can never leak back in through this section. */
export function CareerTimeline({ dated, undated }: { dated: EciCareerItem[]; undated: EciCareerItem[] }) {
  if (dated.length === 0 && undated.length === 0) return null;
  return (
    <div>
      {dated.length > 0 && (
        <ol className="eci-career">
          {dated.map((item, i) => <CareerRow key={i} item={item} />)}
        </ol>
      )}
      {undated.length > 0 && (
        <div style={{ marginTop: dated.length > 0 ? 18 : 0 }}>
          <div className="serif" style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>Postings listed without dates</div>
          <p style={{ fontSize: 12, color: "var(--muted)", margin: "0 0 10px" }}>
            The source lists these without dates. They appear in the source&apos;s order.
          </p>
          <ol className="eci-career">
            {undated.map((item, i) => <CareerRow key={i} item={item} showDate={false} />)}
          </ol>
        </div>
      )}
    </div>
  );
}
