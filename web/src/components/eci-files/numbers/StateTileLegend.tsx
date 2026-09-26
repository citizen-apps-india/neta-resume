import type { EciMetricDef } from "@/lib/eci-numbers";

function Swatch({ style }: { style: React.CSSProperties }) {
  return <span aria-hidden style={{ width: 12, height: 12, borderRadius: 3, flexShrink: 0, ...style }} />;
}

/** The 5-band colour key, plus the 3 special tile states — colour is never the only signal (values print
 *  on the tiles at 480px+, and the table is one tap away), but the key is required reading regardless. */
export function StateTileLegend({ metric }: { metric: EciMetricDef }) {
  return (
    <div className="eci-legend" role="list" aria-label="Tile legend" style={{ marginTop: 16, marginBottom: 8 }}>
      {metric.bandLabels.map((label, i) => (
        <span key={label} role="listitem" className="eci-legend-item">
          <Swatch style={{ background: `var(--eci-seq-${i + 1})`, border: "1px solid var(--rule)" }} />
          {label}
        </span>
      ))}
      <span role="listitem" className="eci-legend-item">
        <Swatch style={{ background: "var(--sunken)", border: "1px dashed var(--border2)" }} />
        No figures yet
      </span>
      <span role="listitem" className="eci-legend-item">
        <Swatch style={{ background: "var(--card)", border: "1px solid var(--rule)" }} />
        Figures on record, not this measure
      </span>
      <span role="listitem" className="eci-legend-item">
        <Swatch style={{ background: "repeating-linear-gradient(45deg, var(--card) 0 3px, var(--rule) 3px 4px)", border: "1px solid var(--rule)" }} />
        Special Revision (Assam), not compared
      </span>
    </div>
  );
}
