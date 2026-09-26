import type { EciCompactEntry } from "@/types/eci-files";
import { eciEntryHref } from "@/lib/eci-files";
import { EntryRow } from "@/components/eci-files/ui/EntryRow";
import { LaneChip } from "@/components/eci-files/ui/LaneChip";
import { StatusWord } from "@/components/eci-files/ui/StatusWord";
import { entryDayLabel, type EciEntryRowUnit, type EciMonthBucket } from "@/components/eci-files/front/entriesGrouping";

/** One folded day: the lead entry as a normal row, the rest behind a native `<details>` toggle on its
 *  status line — no client JS, and no invented collective headline for what's really N separate records. */
function FoldedRow({ entries, preserve }: { entries: EciCompactEntry[]; preserve: Record<string, string | undefined> }) {
  const [lead, ...rest] = entries;
  return (
    <EntryRow
      date={entryDayLabel(lead)}
      lane={lead.lane}
      title={lead.title}
      href={eciEntryHref(lead.id, preserve, "/eci-files/entries")}
      status={lead.status}
      checked={lead.check_status === "checked"}
      extra={
        <details className="eci-fold-more">
          <summary className="mono">+ {rest.length} more record{rest.length === 1 ? "" : "s"} on this day</summary>
          <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 8 }}>
            {rest.map((e) => (
              <div key={e.id} style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                <LaneChip lane={e.lane} size={11} />
                <a href={eciEntryHref(e.id, preserve, "/eci-files/entries")} style={{ fontSize: 13.5, fontWeight: 600, color: "var(--ink)", textDecoration: "none" }}>
                  {e.title}
                </a>
                <StatusWord status={e.status} checked={e.check_status === "checked"} />
              </div>
            ))}
          </div>
        </details>
      }
    />
  );
}

function Row({ unit, preserve }: { unit: EciEntryRowUnit; preserve: Record<string, string | undefined> }) {
  if (Array.isArray(unit)) return <FoldedRow entries={unit} preserve={preserve} />;
  return (
    <EntryRow
      date={entryDayLabel(unit)}
      lane={unit.lane}
      title={unit.title}
      href={eciEntryHref(unit.id, preserve, "/eci-files/entries")}
      status={unit.status}
      checked={unit.check_status === "checked"}
    />
  );
}

/** One month's heading (skipped for the unlabelled year-precision bucket) plus its rows. */
export function EntriesMonthSection({ month, preserve }: { month: EciMonthBucket; preserve: Record<string, string | undefined> }) {
  return (
    <section>
      {month.label && (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", padding: "22px 0 8px" }}>
          <h3 className="serif" style={{ margin: 0, fontSize: 18, fontWeight: 650 }}>{month.label}</h3>
          <span className="mono" style={{ fontSize: 12, color: "var(--muted)" }}>
            {month.count} {month.count === 1 ? "entry" : "entries"}
          </span>
        </div>
      )}
      {month.rows.map((unit) => (
        <Row key={Array.isArray(unit) ? unit[0].id : unit.id} unit={unit} preserve={preserve} />
      ))}
    </section>
  );
}
