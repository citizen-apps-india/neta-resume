import Link from "next/link";
import type { EciEntryRef, EciSelection } from "@/types/eci-files";
import { eciEntryHref, formatEciDate, regimeShortLabel } from "@/lib/eci-files";
import { SelectionSeatsRow } from "@/components/eci-files/people/SelectionSeatsRow";

function CitedLine({ ids, entriesIndex, basePath }: { ids: string[]; entriesIndex: EciEntryRef[]; basePath: string }) {
  if (ids.length === 0) return null;
  const byId = new Map(entriesIndex.map((e) => [e.id, e]));
  return (
    <div className="mono" style={{ fontSize: 10.5, color: "var(--faint)", marginTop: 8 }}>
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

/** "Eight selections, 2019 to today" (C-After-Selections.dc.html): one connected vertical timeline, newest
 *  claims at the bottom exactly as the API orders them, replacing the bipartite selector→appointee graph —
 *  each row is the same `SelectionSeatsRow` a profile's "Selected by" uses, so a panel reads identically in
 *  both places. Dissents are marked twice: the rail dot (`.eci-sel-timeline` in globals.css) and a named
 *  badge, never colour alone. */
export function SelectionTimeline({
  selections, entriesIndex, basePath,
}: {
  selections: EciSelection[];
  entriesIndex: EciEntryRef[];
  basePath: string;
}) {
  return (
    <ol className="eci-sel-timeline">
      {selections.map((sel) => {
        const dissented = sel.dissent.length > 0;
        return (
          <li key={sel.id} id={sel.id} data-dissent={dissented ? "true" : undefined} style={{ scrollMarginTop: 90 }}>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 16, alignItems: "flex-start", justifyContent: "space-between" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 4, minWidth: 96, flexShrink: 0 }}>
                <span className="mono" style={{ fontSize: 12, color: "var(--ink)" }}>{formatEciDate(sel.date, sel.date_precision)}</span>
                <span
                  className="mono"
                  style={{ fontSize: 10.5, color: "var(--ink2)", border: "1px solid var(--rule)", borderRadius: 999, padding: "3px 9px", alignSelf: "flex-start" }}
                >
                  {regimeShortLabel(sel.regime)}
                </span>
              </div>

              <div style={{ flex: 1, minWidth: 280 }}>
                <SelectionSeatsRow sel={sel} basePath={basePath} />
              </div>

              <div style={{ flexShrink: 0 }}>
                {dissented && (
                  <span className="eci-badge" data-part="dissented">
                    Dissent · {sel.dissent.map((d) => d.name).join(", ")}
                  </span>
                )}
              </div>
            </div>
            <CitedLine ids={sel.entry_ids} entriesIndex={entriesIndex} basePath={basePath} />
          </li>
        );
      })}
    </ol>
  );
}
