import type { EciTextStatus } from "@/types/eci-files";
import { ECI_TEXT_STATUS_LABEL, ECI_TEXT_STATUS_SHORT } from "@/lib/eci-files";

/** The provenance of one side of a rule diff — "Verbatim from the document" down to "Paraphrased from
 *  news reports: not the document's wording". Colour is a hint only (verbatim reads calmer than
 *  paraphrase); the words carry the meaning, per house rule. */
export function TextStatusBadge({ status, short = false }: { status: EciTextStatus; short?: boolean }) {
  const calm = status === "verbatim";
  return (
    <span
      className="mono"
      style={{
        display: "inline-flex", alignItems: "center", fontSize: 10.5, fontWeight: 600,
        letterSpacing: "0.02em", padding: "4px 10px", borderRadius: 6,
        border: `1px solid ${calm ? "var(--border2)" : "var(--eci-report)"}`,
        background: calm ? "var(--sunken)" : "color-mix(in srgb, var(--eci-report) 12%, var(--card2))",
        color: calm ? "var(--ink2)" : "var(--eci-report)",
      }}
    >
      {short ? ECI_TEXT_STATUS_SHORT[status] : ECI_TEXT_STATUS_LABEL[status]}
    </span>
  );
}
