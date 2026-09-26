import type { EciObjection } from "@/types/eci-files";
import { eciEntryHrefIn, formatEciDate, linkifyFollowedBy } from "@/lib/eci-files";
import { PersonAvatar } from "@/components/eci-files/views/PersonAvatar";
import { EntryRefLink } from "@/components/eci-files/views/EntryRefLink";

/** One entry name-and-date link, styled small since this is one line among several in the meta column. */
function BySignature({ by }: { by: EciObjection["by"] }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 8 }}>
      {by.map((p) => (
        <div key={p.slug} style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <PersonAvatar name={p.name} photo={p.photo} size={28} decorative />
          <span style={{ fontSize: 11.5, color: "var(--ink2)" }}>{p.name}</span>
        </div>
      ))}
    </div>
  );
}

/** What followed one objection: parses the two token kinds `linkifyFollowedBy` recognises into a drawer
 *  link ("(see entry)") or a same-page anchor ("(objection N)"). */
function FollowedBy({ text, refs }: { text: string | null; refs: EciObjection["followed_by_refs"] }) {
  if (!text) return <span style={{ color: "var(--muted)" }}>Nothing further in the record.</span>;
  const segments = linkifyFollowedBy(text, refs);
  return (
    <>
      {segments.map((seg, i) => {
        if (seg.kind === "text") return <span key={i}>{seg.text}</span>;
        if (seg.kind === "objection") return <a key={i} href={`#objection-${seg.n}`} style={{ color: "var(--eci-ink)" }}>(objection {seg.n})</a>;
        return (
          <a key={i} href={eciEntryHrefIn("/eci-files/objections", seg.id)} style={{ color: "var(--eci-ink)" }}>
            (see entry)
          </a>
        );
      })}
    </>
  );
}

const EMPTY_SLOT_HEADING = "Not itemised in the published reports";
const EMPTY_SLOT_BODY =
  "The Indian Express reported 14 objections. Its published reports describe 11 that this record can match to a dated note or letter.";

/** The fourteen slots: 11 filled from the record, 3 dashed and empty — PHASES-3-5-DECISIONS.md's exact
 *  label for the gap, not a promise that they'll be published later. The data table this section's chart
 *  is a picture of (PHASE5-SPEC §6.2). */
export function ObjectionLedger({ objections, missing }: { objections: EciObjection[]; missing: number }) {
  return (
    <ol className="eci-ledger">
      {objections.map((o) => (
        <li key={o.n} id={`objection-${o.n}`} className="eci-slot">
          <div>
            <div className="mono" style={{ fontSize: 12, color: "var(--muted)" }}>No. {o.n}</div>
            <div className="mono" style={{ fontSize: 11.5, color: "var(--ink2)", marginTop: 2 }}>{formatEciDate(o.date, o.date_precision)}</div>
            <BySignature by={o.by} />
          </div>
          <div>
            <h3 className="serif" style={{ fontSize: 15, fontWeight: 600, lineHeight: 1.4, margin: "0 0 10px" }}>{o.concerns}</h3>
            <div className="mono" style={{ fontSize: 10, letterSpacing: "0.05em", color: "var(--faint)", marginBottom: 4 }}>WHAT FOLLOWED</div>
            <p style={{ fontSize: 13, color: "var(--ink2)", lineHeight: 1.55, margin: "0 0 10px" }}>
              <FollowedBy text={o.followed_by} refs={o.followed_by_refs} />
            </p>
            <div className="mono" style={{ fontSize: 10, letterSpacing: "0.05em", color: "var(--faint)", marginBottom: 4 }}>ENTRIES</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 4, marginBottom: 8 }}>
              {o.entries.map((e) => (
                <EntryRefLink key={e.id} entry={e} basePath="/eci-files/objections" />
              ))}
            </div>
            {!o.public && (
              <span className="mono" style={{ fontSize: 10.5, color: "var(--muted)", border: "1px dashed var(--border2)", borderRadius: 6, padding: "3px 8px" }}>
                Not a public document · described in reporting
              </span>
            )}
          </div>
        </li>
      ))}
      {Array.from({ length: missing }).map((_, i) => (
        <li key={`empty-${i}`} className="eci-slot-empty" aria-label={`Objection ${EMPTY_SLOT_HEADING.toLowerCase()}`}>
          <div className="mono" style={{ fontSize: 13, fontWeight: 600, color: "var(--ink2)", marginBottom: i === 0 ? 6 : 0 }}>
            {EMPTY_SLOT_HEADING}
          </div>
          {i === 0 && <p style={{ fontSize: 12.5, color: "var(--muted)", lineHeight: 1.55, margin: 0 }}>{EMPTY_SLOT_BODY}</p>}
        </li>
      ))}
    </ol>
  );
}
