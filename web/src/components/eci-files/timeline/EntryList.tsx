import type { EciCompactEntry, EciEntryDetail } from "@/types/eci-files";
import type { EciMonthBlock } from "@/lib/eci-timeline-client";
import { DAY_FOLD_THRESHOLD } from "@/lib/eci-timeline-client";
import { formatEciDate } from "@/lib/eci-files";
import { EntryRow } from "@/components/eci-files/ui/EntryRow";
import { EntryExpanded } from "@/components/eci-files/timeline/EntryExpanded";

/** "2 Jan" / "Jan 2026" / "2026" / "—" — the row's own date, next to a month heading that already carries
 *  the year, so the row never repeats it. */
function rowDate(entry: Pick<EciCompactEntry, "date" | "date_precision">): string {
  if (!entry.date) return "—";
  const full = formatEciDate(entry.date, entry.date_precision);
  if (entry.date_precision !== "day") return full;
  const d = new Date(`${entry.date}T00:00:00Z`);
  if (isNaN(d.getTime())) return full;
  return full.replace(/\s\d{4}$/, "");
}

function DuplicateExtras({ extra, onOpenEntry }: { extra: EciCompactEntry[]; onOpenEntry: (id: string) => void }) {
  return (
    <ul style={{ listStyle: "none", margin: "6px 0 0", padding: "8px 0 0 16px", borderLeft: "2px solid var(--rule2)", display: "flex", flexDirection: "column", gap: 6 }}>
      {extra.map((e) => (
        <li key={e.id} style={{ fontSize: 13 }}>
          <button
            type="button"
            onClick={() => onOpenEntry(e.id)}
            style={{ border: 0, background: "none", padding: 0, textAlign: "left", color: "var(--ink2)", cursor: "pointer", font: "inherit", textDecoration: "underline", textDecorationColor: "var(--rule)" }}
          >
            {e.title}
          </button>
        </li>
      ))}
    </ul>
  );
}

export function EntryList({
  monthBlocks, expandedId, expandedDetail, expandedLoading, expandedError, keyMomentIds,
  onOpenEntry, onCollapse, onPrev, onNext, canPrev, canNext, expandedDays, onToggleDay,
  expandedClusters, onToggleCluster, highlightId, buildShareUrl,
}: {
  monthBlocks: EciMonthBlock[];
  expandedId: string | null;
  expandedDetail: EciEntryDetail | null;
  expandedLoading: boolean;
  expandedError: boolean;
  keyMomentIds: Set<string>;
  onOpenEntry: (id: string) => void;
  onCollapse: () => void;
  onPrev: () => void;
  onNext: () => void;
  canPrev: boolean;
  canNext: boolean;
  expandedDays: Set<string>;
  onToggleDay: (key: string) => void;
  expandedClusters: Set<string>;
  onToggleCluster: (keptId: string) => void;
  highlightId: string | null;
  buildShareUrl: (id: string) => string;
}) {
  if (monthBlocks.length === 0) {
    return <p style={{ color: "var(--muted)", fontSize: 14, padding: "18px 0" }}>No entries match the current filters in this period.</p>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column" }}>
      {monthBlocks.map((month) => (
        <div key={month.key}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", padding: "22px 0 8px" }}>
            <h3 style={{ margin: 0, fontSize: 18, fontWeight: 650 }}>{month.label}</h3>
            <span className="mono" style={{ fontSize: 12, color: "var(--muted)" }}>{month.total} {month.total === 1 ? "entry" : "entries"}</span>
          </div>

          {month.days.map((day) => {
            const dayKey = `${month.key}:${day.date ?? "undated"}`;
            const folded = day.rawCount >= DAY_FOLD_THRESHOLD && !expandedDays.has(dayKey);

            if (folded) {
              return (
                <div
                  key={dayKey}
                  id={`eci-row-day:${dayKey}`}
                  style={{
                    display: "grid", gridTemplateColumns: "64px minmax(0, 1fr)", gap: 16, padding: "14px 0",
                    borderTop: "1px solid var(--rule)", outline: highlightId === dayKey ? "2px solid var(--eci-ink)" : "none", outlineOffset: 2,
                  }}
                >
                  <div className="mono" style={{ fontSize: 12.5, color: "var(--muted)", paddingTop: 2 }}>{day.date ? rowDate({ date: day.date, date_precision: "day" }) : "—"}</div>
                  <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
                    <span style={{ fontSize: 14, color: "var(--ink2)" }}>{day.rawCount} entries on this day</span>
                    <button type="button" onClick={() => onToggleDay(dayKey)} className="mono" style={{ border: 0, background: "none", padding: 0, fontSize: 12.5, color: "var(--eci-ink)", cursor: "pointer" }}>
                      Show all
                    </button>
                  </div>
                </div>
              );
            }

            return (
              <div key={dayKey}>
                {day.rawCount >= DAY_FOLD_THRESHOLD && (
                  <div style={{ display: "flex", justifyContent: "flex-end", padding: "6px 0" }}>
                    <button type="button" onClick={() => onToggleDay(dayKey)} className="mono" style={{ border: 0, background: "none", padding: 0, fontSize: 12, color: "var(--muted)", cursor: "pointer" }}>
                      Collapse {formatEciDate(day.date, "day")}
                    </button>
                  </div>
                )}
                {day.clusters.map((cluster) => {
                  const entry = cluster.kept;
                  const isExpanded = expandedId === entry.id;
                  const isKeyMoment = keyMomentIds.has(entry.id);
                  const showingExtra = expandedClusters.has(entry.id);

                  if (isExpanded) {
                    return (
                      <div key={entry.id} id={`eci-row-${entry.id}`} style={{ display: "grid", gridTemplateColumns: "64px minmax(0, 1fr)", gap: 16, padding: "18px 0", borderTop: "1px solid var(--rule)" }}>
                        <div className="mono" style={{ fontSize: 12.5, color: "var(--muted)", paddingTop: 4 }}>{rowDate(entry)}</div>
                        {expandedDetail && expandedDetail.id === entry.id ? (
                          <EntryExpanded
                            entry={expandedDetail}
                            isKeyMoment={isKeyMoment}
                            onOpenEntry={onOpenEntry}
                            onCollapse={onCollapse}
                            onPrev={onPrev}
                            onNext={onNext}
                            canPrev={canPrev}
                            canNext={canNext}
                            shareUrl={buildShareUrl(entry.id)}
                          />
                        ) : expandedError ? (
                          <div style={{ fontSize: 14, color: "var(--muted)" }}>This entry didn&apos;t load — try again in a moment.</div>
                        ) : (
                          <div style={{ fontSize: 14, color: "var(--muted)" }}>{expandedLoading ? "Loading…" : ""}</div>
                        )}
                      </div>
                    );
                  }

                  return (
                    <div key={entry.id} id={`eci-row-${entry.id}`} style={{ outline: highlightId === entry.id ? "2px solid var(--eci-ink)" : "none", outlineOffset: -2, borderRadius: 8 }}>
                      <EntryRow
                        date={rowDate(entry)}
                        lane={entry.lane}
                        title={entry.title}
                        onClick={() => onOpenEntry(entry.id)}
                        status={entry.status}
                        checked={entry.check_status === "checked"}
                        emphasis={isKeyMoment}
                        extra={
                          cluster.extra.length > 0 ? (
                            <button
                              type="button"
                              onClick={() => onToggleCluster(entry.id)}
                              style={{ border: 0, background: "none", padding: 0, fontSize: 12.5, color: "var(--eci-ink)", cursor: "pointer" }}
                            >
                              {showingExtra ? "Hide" : `+ ${cluster.extra.length} more record${cluster.extra.length === 1 ? "" : "s"} of this`}
                            </button>
                          ) : undefined
                        }
                      />
                      {showingExtra && <DuplicateExtras extra={cluster.extra} onOpenEntry={onOpenEntry} />}
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}
