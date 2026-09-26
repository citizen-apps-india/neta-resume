import Link from "next/link";
import type { EciEntryRef, EciSelectionRegime } from "@/types/eci-files";
import { eciEntryHref, formatLooseDate } from "@/lib/eci-files";

const SEATS: Record<string, { label: string; filled: boolean }[]> = {
  convention: [{ label: "Government", filled: true }],
  baranwal: [{ label: "PM", filled: true }, { label: "LoP", filled: false }, { label: "CJI", filled: false }],
  act_2023: [{ label: "PM", filled: true }, { label: "PM's minister", filled: true }, { label: "LoP", filled: false }],
};

function SeatDiagram({ regimeKey }: { regimeKey: string }) {
  const seats = SEATS[regimeKey] ?? [];
  const w = seats.length * 56;
  return (
    <div>
      <svg width={w} height={44} viewBox={`0 0 ${w} 44`} role="img" aria-label={`Seats: ${seats.map((s) => `${s.label} (${s.filled ? "chosen by the government" : "not chosen by the government"})`).join(", ")}`}>
        {seats.map((s, i) => (
          <g key={i} transform={`translate(${i * 56 + 28}, 14)`}>
            <circle r={12} className={s.filled ? "eci-seat-gov" : "eci-seat-hollow"} />
            <text y={26} textAnchor="middle" fontSize={9.5} fill="var(--muted)">{s.label}</text>
          </g>
        ))}
      </svg>
      {regimeKey === "convention" && (
        <p style={{ fontSize: 11.5, color: "var(--muted)", margin: "2px 0 0" }}>No committee</p>
      )}
    </div>
  );
}

/** The three regime cards on `/eci-files/selections` (PHASE4-SPEC.md §3, step 2): rule, panel, a 3-seat
 *  diagram (filled = chosen by the government, stated in text as well as fill), and the selections cited
 *  to it. */
export function RegimeCompare({ regimes, entriesIndex }: { regimes: EciSelectionRegime[]; entriesIndex: EciEntryRef[] }) {
  const byId = new Map(entriesIndex.map((e) => [e.id, e]));
  return (
    <div className="eci-regime-grid" style={{ marginBottom: 26 }}>
      {regimes.map((r) => (
        <div key={r.key} id={`regime-${r.key}`} style={{ border: "1px solid var(--rule)", borderRadius: 12, background: "var(--card2)", padding: "16px 18px" }}>
          <div className="serif" style={{ fontSize: 15.5, fontWeight: 600, marginBottom: 2 }}>{r.label}</div>
          <div className="mono" style={{ fontSize: 11, color: "var(--muted)", marginBottom: 10 }}>
            {r.from_date ? formatLooseDate(r.from_date) : "before 2019"} – {r.to_date ? formatLooseDate(r.to_date) : "present"}
          </div>
          <p style={{ fontSize: 12.5, color: "var(--ink2)", lineHeight: 1.5, margin: "0 0 12px" }}>{r.rule}</p>
          <SeatDiagram regimeKey={r.key} />
          <p className="mono" style={{ fontSize: 11.5, color: "var(--ink2)", margin: "10px 0 0" }}>
            {r.selection_count} selection{r.selection_count === 1 ? "" : "s"} made under this rule
          </p>
          {r.notes && <p style={{ fontSize: 12, color: "var(--muted)", fontStyle: "italic", margin: "8px 0 0" }}>{r.notes}</p>}
          {r.entry_ids.length > 0 && (
            <div className="mono" style={{ fontSize: 10.5, color: "var(--faint)", marginTop: 10 }}>
              Cited:{" "}
              {r.entry_ids.map((id, i) => (
                <span key={id}>
                  {i > 0 && ", "}
                  <Link href={eciEntryHref(id, {}, "/eci-files/selections")} style={{ color: "var(--accent-2)" }}>
                    {byId.get(id)?.title ?? id}
                  </Link>
                </span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
