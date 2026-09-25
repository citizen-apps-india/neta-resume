import type { EciHeadlineStat } from "@/types/eci-files";

/** One headline number, its label, and its tappable source (REDESIGN-SPEC §"Web": "the four headline
 *  stats, each with a tappable source"). The value is a curated display string, not a raw number — it
 *  comes pre-formatted from `data/eci_files/headline.json` so the web never guesses a unit. */
function HeroStatTile({ s }: { s: EciHeadlineStat }) {
  return (
    <div className="eci-hero-tile" style={{ borderRadius: 14 }}>
      <div className="mono eci-hero-value" style={{ fontSize: "clamp(24px,4.6vw,32px)" }}>{s.value}</div>
      <div style={{ fontSize: 12.5, color: "var(--ink2)", lineHeight: 1.35, margin: "4px 0 10px" }}>{s.label}</div>
      <a
        href={s.source_url}
        target="_blank"
        rel="noopener noreferrer"
        className="mono tap"
        style={{
          display: "inline-flex", alignItems: "center", gap: 5, fontSize: 10.5, color: "var(--eci-ink)",
          textDecoration: "none", border: "1px solid var(--rule)", borderRadius: 6, padding: "4px 8px",
        }}
      >
        ↗ {s.source_label}
      </a>
    </div>
  );
}

export function HeroStats({ headline }: { headline: EciHeadlineStat[] }) {
  if (headline.length === 0) return null;
  return (
    <div className="nr-statgrid" style={{ marginBottom: 28 }}>
      {headline.map((s) => (
        <HeroStatTile key={s.entry_id + s.label} s={s} />
      ))}
    </div>
  );
}
