import Link from "next/link";
import { getEciSummary, type EciSummary } from "@/lib/api";

/** The Elections page's way into ECI Files: three sourced headline figures and one link. Renders the link
 *  alone if the record can't be fetched. */
export async function EciFilesFeature() {
  let summary: EciSummary | null = null;
  try {
    summary = await getEciSummary();
  } catch {
    summary = null;
  }
  const figures = (summary?.headline ?? []).slice(0, 3);
  return (
    <section aria-labelledby="eci-files-feature" style={{ marginBottom: 36, border: "1px solid var(--rule)", borderRadius: 16, background: "var(--card)", padding: "clamp(18px,3vw,26px)", display: "flex", flexDirection: "column", gap: 18 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: 16, flexWrap: "wrap" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <span className="mono" style={{ fontSize: 11, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--eci-ink)" }}>ECI Files</span>
          <h2 id="eci-files-feature" className="serif" style={{ margin: 0, fontSize: "clamp(20px,3.4vw,26px)", fontWeight: 600, letterSpacing: "-0.01em" }}>
            The Election Commission, on the record
          </h2>
          <p style={{ margin: 0, fontSize: 14, color: "var(--ink2)" }}>
            {summary ? `${summary.counts.dated_entries ?? summary.counts.entries} sourced entries, 2019 to today.` : "Every decision, rule and court order, sourced."}
          </p>
        </div>
        <Link href="/eci-files" style={{ display: "inline-flex", alignItems: "center", minHeight: 44, padding: "0 18px", borderRadius: 12, background: "var(--eci-ink)", color: "var(--card)", fontWeight: 600, fontSize: 14, textDecoration: "none" }}>
          Open ECI Files →
        </Link>
      </div>
      {figures.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 200px), 1fr))", gap: 12 }}>
          {figures.map((f) => (
            <div key={f.label} style={{ display: "flex", flexDirection: "column", gap: 4, padding: "12px 14px", borderRadius: 12, background: "var(--sunken)" }}>
              <span className="mono" style={{ fontSize: 24, fontWeight: 600, color: "var(--eci-ink)" }}>{f.value}</span>
              <span style={{ fontSize: 13, color: "var(--ink2)", lineHeight: 1.35 }}>{f.label}</span>
              {f.source_url && (
                <a href={f.source_url} target="_blank" rel="noopener noreferrer" className="mono" style={{ fontSize: 10.5, color: "var(--muted)" }}>
                  {f.source_label} ↗
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
