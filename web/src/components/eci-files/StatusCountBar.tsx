import type { EciStatusCounts } from "@/types/eci-files";
import { ECI_STATUS_META, formatStatusCounts } from "@/lib/eci-files";

const ORDER: (keyof EciStatusCounts)[] = ["documented", "reported", "claim", "response"];

/** A 4px stacked bar of the four trust tokens, width proportional to counts — purely decorative, the
 *  mono count text next to it is what actually carries the information (PHASE4-SPEC.md §1.3). */
export function StatusCountBar({ counts, width = 120 }: { counts: EciStatusCounts; width?: number }) {
  const total = ORDER.reduce((s, k) => s + counts[k], 0);
  if (total === 0) return null;
  return (
    <div aria-hidden style={{ display: "flex", height: 4, width, borderRadius: 2, overflow: "hidden", background: "var(--rule2)" }}>
      {ORDER.filter((k) => counts[k] > 0).map((k) => (
        <span key={k} style={{ flex: counts[k], background: ECI_STATUS_META[k].token }} />
      ))}
    </div>
  );
}

/** `StatusCountBar` plus the count text it echoes — `KeyFacts`'s "Entries on record" tile. */
export function EntryCountLine({ counts, total }: { counts: EciStatusCounts; total: number }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <StatusCountBar counts={counts} />
      <span className="mono" style={{ fontSize: 10.5, color: "var(--faint)" }}>{formatStatusCounts(total, counts)}</span>
    </div>
  );
}
