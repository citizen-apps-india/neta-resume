import type { EciPersonSummary } from "@/types/eci-files";
import { NamedPeopleList } from "@/components/eci-files/NamedPeopleList";

/** "Also named in the record" (C-After-People.dc.html): collapsed by default behind one dashed panel, not
 *  a section of its own — judges, ministers and opposition leaders quoted or cited, never office-holders
 *  at the Commission, so they read as an appendix rather than a fourth peer group. */
export function AlsoNamedPanel({ people }: { people: EciPersonSummary[] }) {
  if (people.length === 0) return null;
  return (
    <details id="named" className="eci-more" style={{ border: "1px dashed var(--border2)", borderRadius: 12, background: "var(--card)", padding: "16px 18px", scrollMarginTop: 90 }}>
      <summary style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, flexWrap: "wrap", cursor: "pointer", listStyle: "none" }}>
        <span style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <span style={{ fontSize: 14, fontWeight: 650 }}>Also named in the record</span>
          <span style={{ fontSize: 12, color: "var(--muted)" }}>
            Judges, ministers, opposition leaders and other officials quoted or cited, not office-holders at the Commission.
          </span>
        </span>
        <span
          className="mono"
          style={{ flexShrink: 0, minHeight: 40, display: "inline-flex", alignItems: "center", padding: "0 16px", borderRadius: 10, border: "1px solid var(--border)", background: "var(--bg)", fontSize: 13.5, color: "var(--ink)" }}
        >
          Show all {people.length}
        </span>
      </summary>
      <div style={{ marginTop: 14 }}>
        <NamedPeopleList people={people} />
      </div>
    </details>
  );
}
