import Link from "next/link";
import type { EciEntryRef, EciSelection } from "@/types/eci-files";
import { eciEntryHref, formatEciDate, regimeShortLabel } from "@/lib/eci-files";
import { SelectionSeatsRow } from "@/components/eci-files/people/SelectionSeatsRow";

function CitedLine({ ids, entriesIndex, basePath }: { ids: string[]; entriesIndex: EciEntryRef[]; basePath: string }) {
  if (ids.length === 0) return null;
  const byId = new Map(entriesIndex.map((e) => [e.id, e]));
  return (
    <div className="mono" style={{ fontSize: 10.5, color: "var(--faint)" }}>
      Cited:{" "}
      {ids.map((id, i) => (
        <span key={id}>
          {i > 0 && ", "}
          <Link href={eciEntryHref(id, {}, basePath)} style={{ color: "var(--accent-2)" }}>{byId.get(id)?.title ?? id}</Link>
        </span>
      ))}
    </div>
  );
}

/** "Selected by" as one card of panel seats (C-After-Profile.dc.html): every selection where this person
 *  is an appointee, newest first (already the API's sort order), each one `SelectionSeatsRow` with this
 *  person's own seat highlighted. Falls back to `details.selection` when the record has no selection row
 *  at all (people appointed before `selections.json`'s 2019 window). */
export function SelectedByBlock({
  slug, selections, entriesIndex, basePath, fallback,
}: {
  slug: string;
  selections: EciSelection[];
  entriesIndex: EciEntryRef[];
  basePath: string;
  fallback?: { selection: string; sourceUrl: string | null };
}) {
  const mine = selections.filter((s) => s.appointed.some((a) => a.person_slug === slug));

  if (mine.length === 0) {
    if (!fallback) return null;
    return (
      <section>
        <h2 className="serif" style={{ fontSize: 17, fontWeight: 650, margin: "0 0 10px" }}>Selected by</h2>
        <div style={{ border: "1px solid var(--rule)", borderRadius: 14, background: "var(--card)", padding: "18px 20px" }}>
          <div className="mono" style={{ fontSize: 10, color: "var(--faint)", marginBottom: 6 }}>FROM THE PROFILE</div>
          <p style={{ fontSize: 13.5, color: "var(--ink2)", lineHeight: 1.55, margin: 0 }}>{fallback.selection}</p>
          {fallback.sourceUrl && (
            <a href={fallback.sourceUrl} target="_blank" rel="noopener noreferrer" className="mono" style={{ fontSize: 11, color: "var(--accent-2)" }}>
              source ↗
            </a>
          )}
        </div>
      </section>
    );
  }

  return (
    <section>
      <h2 className="serif" style={{ fontSize: 17, fontWeight: 650, margin: "0 0 10px" }}>Selected by</h2>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {mine.map((sel) => (
          <div key={sel.id} id={sel.id} style={{ border: "1px solid var(--rule)", borderRadius: 14, background: "var(--card)", padding: "18px 20px", scrollMarginTop: 90 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap", gap: 8, marginBottom: 12 }}>
              <span className="mono" style={{ fontSize: 11.5, color: "var(--muted)" }}>{formatEciDate(sel.date, sel.date_precision)}</span>
              <Link
                href={`/eci-files/selections#regime-${sel.regime}`}
                className="mono"
                style={{ fontSize: 10.5, fontWeight: 600, color: "var(--eci-ink)", textDecoration: "none" }}
              >
                {regimeShortLabel(sel.regime)}
              </Link>
            </div>
            <SelectionSeatsRow sel={sel} highlightSlug={slug} basePath={basePath} />
            <div style={{ marginTop: 10 }}>
              <CitedLine ids={sel.entry_ids} entriesIndex={entriesIndex} basePath={basePath} />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
