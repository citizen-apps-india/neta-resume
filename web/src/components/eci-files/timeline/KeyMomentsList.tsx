import type { EciEntry } from "@/types/eci-files";
import { formatEciDate } from "@/lib/eci-files";

/** "Jump to a key moment" (DESIGN-BRIEF): the ids the API's `/eci-files/summary` already curates.
 *  Jumping moves the window to include that date and opens the entry in place — it isn't a real link, so
 *  it's a `<button>`, matching {@link EntryRow}'s own "state change, not navigation" rule. */
export function KeyMomentsList({ moments, onJump }: { moments: EciEntry[]; onJump: (id: string) => void }) {
  if (moments.length === 0) return null;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, background: "var(--card)", border: "1px solid var(--rule)", borderRadius: 14, padding: "18px 20px" }}>
      <h2 style={{ margin: "0 0 6px", fontSize: 16, fontWeight: 650 }}>Jump to a key moment</h2>
      {moments.map((m) => (
        <button
          key={m.id}
          type="button"
          onClick={() => onJump(m.id)}
          style={{
            display: "grid", gridTemplateColumns: "76px 10px minmax(0,1fr)", gap: 8, alignItems: "baseline",
            border: 0, borderTop: "1px solid var(--rule2)", background: "none", padding: "6px 0", margin: 0,
            textAlign: "left", cursor: "pointer", color: "var(--ink)", fontSize: 13, lineHeight: 1.35, fontFamily: "inherit",
          }}
        >
          <span className="mono" style={{ fontSize: 11.5, color: "var(--muted)" }}>{formatEciDate(m.date, m.date_precision)}</span>
          <span aria-hidden style={{ width: 8, height: 8, borderRadius: "50%", background: `var(--eci-lane-${m.lane})`, display: "inline-block" }} />
          <span>{m.title}</span>
        </button>
      ))}
    </div>
  );
}
