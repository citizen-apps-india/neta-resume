import Link from "next/link";
import type { ReactNode } from "react";
import type { EciRuleDiff } from "@/types/eci-files";
import { diffLines } from "@/lib/eci-diff";
import { TextStatusBadge } from "@/components/eci-files/views/TextStatusBadge";
import { formatEciDate } from "@/lib/eci-files";

/** The one changed line worth previewing on a card too small for the full diff: the first line where
 *  `before` and `after` actually differ, or — for a pure insertion/deletion — the line just past where
 *  they stop matching. */
function pickPreview(diff: EciRuleDiff): { before: string; after: string } {
  const { before, after } = diff;
  const n = Math.min(before.length, after.length);
  for (let i = 0; i < n; i++) {
    if (before[i] !== after[i]) return { before: before[i], after: after[i] };
  }
  if (after.length > before.length) return { before: before[n - 1] ?? "", after: after[n] };
  if (before.length > after.length) return { before: before[n], after: after[n - 1] ?? "" };
  return { before: before[0] ?? "", after: after[0] ?? "" };
}

/** One "Before and after" card on `/eci-files/rules`: the title, whether it's verbatim or paraphrased,
 *  and a short real preview — the before line struck through, the after line with its changed words
 *  marked — so a reader sees the shape of the change before opening the full diff (PHASE5-SPEC §6.4,
 *  design brief "comparison cards each with a short real before→after preview"). */
export function RuleComparisonCard({ diff }: { diff: EciRuleDiff }) {
  const preview = pickPreview(diff);
  const [op] = diffLines([preview.before], [preview.after]);
  const afterNode: ReactNode = op && op.kind === "change"
    ? op.after.map((s, i) => (s.changed ? <mark key={i} className="eci-rule-card-mark">{s.text}</mark> : <span key={i}>{s.text}</span>))
    : preview.after;

  return (
    <Link href={`/eci-files/rules/${diff.id}`} className="eci-rule-card lift tap">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 8 }}>
        <span className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>{formatEciDate(diff.rule_entry.date, diff.rule_entry.date_precision)}</span>
        <TextStatusBadge status={diff.text_status} short />
      </div>
      <b className="serif" style={{ fontSize: 15, lineHeight: 1.35 }}>{diff.title}</b>
      <div className="eci-rule-card-preview">
        <span className="eci-rule-card-before">{preview.before || "—"}</span>
        <span className="eci-rule-card-after">{afterNode || "—"}</span>
      </div>
    </Link>
  );
}
