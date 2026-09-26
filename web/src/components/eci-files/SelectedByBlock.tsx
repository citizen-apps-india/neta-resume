import type { EciEntryRef, EciSelection } from "@/types/eci-files";
import { SelectionCard } from "@/components/eci-files/SelectionCard";

/** "Selected by" (PHASE4-SPEC.md §2.5.1): every selection where this person is an appointee, newest
 *  first (already the API's sort order). Falls back to `details.selection` when the record has no
 *  selection row at all (people appointed before `selections.json`'s 2019 window). */
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
        <div className="mono" style={{ fontSize: 9.5, letterSpacing: "0.06em", color: "var(--faint)", marginBottom: 6 }}>SELECTED BY</div>
        <div className="mono" style={{ fontSize: 10, color: "var(--faint)", marginBottom: 6 }}>FROM THE PROFILE</div>
        <p style={{ fontSize: 13.5, color: "var(--ink2)", lineHeight: 1.55 }}>{fallback.selection}</p>
        {fallback.sourceUrl && (
          <a href={fallback.sourceUrl} target="_blank" rel="noopener noreferrer" className="mono" style={{ fontSize: 11, color: "var(--accent-2)" }}>
            source ↗
          </a>
        )}
      </section>
    );
  }

  return (
    <section>
      {mine.map((sel) => (
        <SelectionCard key={sel.id} sel={sel} viewerSlug={slug} showAppointees={false} entriesIndex={entriesIndex} basePath={basePath} />
      ))}
    </section>
  );
}
