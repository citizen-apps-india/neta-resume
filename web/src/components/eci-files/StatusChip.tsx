import type { EciEntryStatus } from "@/types/eci-files";
import { eciStatusMeta } from "@/lib/eci-files";

/** "Document / Reported / Claim / Response" — a provenance label, never a verdict on the underlying fact. */
export function StatusChip({ status }: { status: EciEntryStatus }) {
  const m = eciStatusMeta(status);
  return (
    <span
      className="mono"
      style={{
        display: "inline-flex", alignItems: "center", fontSize: 10.5, fontWeight: 600,
        letterSpacing: "0.04em", padding: "4px 10px", borderRadius: 6,
        border: `1px solid ${m.bd}`, background: m.bg, color: m.fg, whiteSpace: "nowrap",
      }}
    >
      {m.label.toUpperCase()}
    </span>
  );
}
