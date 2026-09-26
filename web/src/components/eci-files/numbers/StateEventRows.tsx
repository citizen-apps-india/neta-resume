import Link from "next/link";
import { EntryRow } from "@/components/eci-files/ui/EntryRow";
import { eciEntryHref, formatEciDate } from "@/lib/eci-files";
import type { EciCompactEntry } from "@/types/eci-files";

const SHOWN = 8;

/** "Events behind these numbers" (docs/eci-files/designs/B-After-State.dc.html): compact, equal-weight
 *  rows — the shared {@link EntryRow}, not another chart competing with the waterfall hero above. Prefers
 *  the entries that carry the roll figures and the major court/tribunal actions (`commission`/`courts`
 *  lanes); falls back to the full chronological set when a state has too few of those to be worth the
 *  distinction. Capped at {@link SHOWN}, with a link to the rest on the lane timeline. */
export function StateEventRows({
  entries, regionName, basePath, state,
}: {
  entries: EciCompactEntry[];
  regionName: string;
  basePath: string;
  state: string;
}) {
  const dated = entries.filter((e): e is EciCompactEntry & { date: string } => Boolean(e.date));
  if (dated.length === 0) {
    return <p style={{ fontSize: 13.5, color: "var(--muted)" }}>No entries name {regionName} yet.</p>;
  }

  const material = dated.filter((e) => e.lane === "commission" || e.lane === "courts");
  const pool = material.length >= 4 ? material : dated;
  const chronological = pool.slice().sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));
  const shown = chronological.slice(0, SHOWN);

  return (
    <div>
      <div>
        {shown.map((e) => (
          <EntryRow
            key={e.id}
            date={formatEciDate(e.date, e.date_precision)}
            lane={e.lane}
            title={e.title}
            href={eciEntryHref(e.id, {}, basePath)}
            status={e.status}
            checked={e.check_status === "checked"}
          />
        ))}
      </div>
      <div style={{ marginTop: 10 }}>
        <Link
          href={`/eci-files/timeline?state=${state}`}
          className="mono"
          style={{ fontSize: 12.5, color: "var(--accent-2)", textDecoration: "none" }}
        >
          See all {dated.length} {regionName} entries on the timeline →
        </Link>
      </div>
    </div>
  );
}
