import type { EciEntry } from "@/types/eci-files";
import { groupEciTimeline } from "@/lib/eci-files";
import { EntryCard } from "@/components/eci-files/EntryCard";

/** Entries grouped by year, then month (year-precision entries sit unlabelled at the top of their year,
 *  since no month is on record for them). Shared by the main timeline and a person's profile timeline. */
export function Timeline({ entries }: { entries: EciEntry[] }) {
  if (entries.length === 0) {
    return <p style={{ fontSize: 13.5, color: "var(--muted)", padding: "20px 2px" }}>No entries on record.</p>;
  }
  const groups = groupEciTimeline(entries);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
      {groups.map((yg) => (
        <section key={yg.year}>
          <h2 className="serif" style={{ fontSize: 22, fontWeight: 500, margin: "0 0 8px", color: "var(--ink)" }}>
            {yg.year}
          </h2>
          {yg.months.map((mg, i) => (
            <div key={mg.label ?? `${yg.year}-none-${i}`} style={{ marginBottom: 4 }}>
              {mg.label && (
                <div className="mono" style={{ fontSize: 10.5, letterSpacing: "0.08em", color: "var(--faint)", margin: "10px 0 2px" }}>
                  {mg.label.toUpperCase()}
                </div>
              )}
              {mg.entries.map((e) => (
                <EntryCard key={e.id} entry={e} allEntries={entries} />
              ))}
            </div>
          ))}
        </section>
      ))}
    </div>
  );
}
