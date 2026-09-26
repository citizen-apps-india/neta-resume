import type { ReactNode } from "react";
import Link from "next/link";
import { eciEntryHref, tokenizeEntryIds } from "@/lib/eci-files";
import type { EciRegionSummary } from "@/types/eci-files";

const STAGE_LABEL: Record<string, string> = {
  before: "Before the SIR", draft: "Draft roll", final: "Final roll",
  appeals_filed: "Appeals filed", appeals_pending: "Appeals still pending", restored: "Restored after appeal",
};

/** Linkifies any entry-id-shaped token to `?entry=<id>` on this page (rendered plainly, verbatim — no
 *  rewording). The drawer renders nothing if the id doesn't exist, same as elsewhere. */
function linkify(text: string, basePath: string): ReactNode[] {
  return tokenizeEntryIds(text).map((token, i) =>
    token.kind === "text"
      ? token.text
      : <Link key={i} href={eciEntryHref(token.id, {}, basePath)} style={{ color: "var(--accent-2)" }}>{token.id}</Link>,
  );
}

/** The state's own notes paragraph, then one paragraph per stage that carries a note
 *  (PHASE3-SPEC.md §3.6). */
export function StateNotes({ region, notes, basePath }: { region: EciRegionSummary; notes: string | null; basePath: string }) {
  const stageNotes = region.stages.filter((s) => s.note);
  if (!notes && stageNotes.length === 0) return null;

  return (
    <section style={{ marginBottom: 30 }}>
      <h2 className="serif" style={{ fontSize: 17, fontWeight: 600, margin: "0 0 12px" }}>Notes and conflicts in the record</h2>
      <div style={{ display: "flex", flexDirection: "column", gap: 10, fontSize: 13.5, color: "var(--ink2)", lineHeight: 1.55, maxWidth: "72ch" }}>
        {notes && <p style={{ margin: 0 }}>{linkify(notes, basePath)}</p>}
        {stageNotes.map((s) => (
          <p key={s.stage} style={{ margin: 0 }}>
            <strong style={{ color: "var(--ink)" }}>{STAGE_LABEL[s.stage] ?? s.stage}: </strong>
            {linkify(s.note!, basePath)}
          </p>
        ))}
      </div>
    </section>
  );
}
