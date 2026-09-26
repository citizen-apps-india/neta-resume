import Link from "next/link";
import type { EciObjection } from "@/types/eci-files";
import { eciEntryHref, formatEciDate, linkifyFollowedBy } from "@/lib/eci-files";
import { PersonAvatar } from "@/components/eci-files/views/PersonAvatar";
import { EntryRefLink } from "@/components/eci-files/views/EntryRefLink";

const EMPTY_SLOT_HEADING = "Not itemised in the published reports";

/** What followed one objection, linkified — the same two token kinds `linkifyFollowedBy` recognises,
 *  rendered as a drawer link or a same-page anchor into this list. */
function FollowedBy({ text, refs }: { text: string | null; refs: EciObjection["followed_by_refs"] }) {
  if (!text) return <span style={{ color: "var(--muted)" }}>Nothing further in the record.</span>;
  return (
    <>
      {linkifyFollowedBy(text, refs).map((seg, i) => {
        if (seg.kind === "text") return <span key={i}>{seg.text}</span>;
        if (seg.kind === "objection") return <a key={i} href={`#eci2-objection-${seg.n}`} style={{ color: "var(--eci-ink)" }}>(objection {seg.n})</a>;
        return (
          <a key={i} href={eciEntryHref(seg.id, {}, "/eci-files/objections")} style={{ color: "var(--eci-ink)" }}>
            (see entry)
          </a>
        );
      })}
    </>
  );
}

/** One objection as a short row — number, date, who, a one-line title — with its detail (what followed,
 *  the entries it's sourced to) behind a native, keyboard- and screen-reader-operable `<details>` rather
 *  than always open. Matches `docs/eci-files/designs/D-After-Objections.dc.html`'s "Details"/"Hide" rows. */
function ObjectionRow({ o }: { o: EciObjection }) {
  const joint = o.by.length > 1;
  return (
    <details className="eci2-obj-row" id={`eci2-objection-${o.n}`}>
      <summary className="eci2-obj-summary">
        <span className="mono eci2-obj-n">{String(o.n).padStart(2, "0")}</span>
        <span className="mono eci2-obj-date">{formatEciDate(o.date, o.date_precision)}</span>
        <span className="eci2-obj-by">
          {o.by.map((p) => (
            <PersonAvatar key={p.slug} name={p.name} photo={p.photo} size={24} decorative />
          ))}
          <span className="eci2-obj-by-name">{joint ? "Both commissioners" : o.by[0]?.name}</span>
        </span>
        <span className="eci2-obj-title">{o.concerns}</span>
        <span className="eci2-obj-toggle mono">
          <span className="eci2-obj-toggle-open">Details</span>
          <span className="eci2-obj-toggle-close">Hide</span>
          <svg width="12" height="12" viewBox="0 0 14 14" fill="none" aria-hidden="true" className="eci2-chevron">
            <path d="M3.5 5.5L7 9l3.5-3.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
      </summary>
      <div className="eci2-obj-detail">
        <div className="mono eci2-cell-label">What followed</div>
        <p style={{ fontSize: 13, lineHeight: 1.55, color: "var(--ink2)", margin: "0 0 10px" }}>
          <FollowedBy text={o.followed_by} refs={o.followed_by_refs} />
        </p>
        <div className="mono eci2-cell-label">Entries</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 4, marginBottom: o.public ? 0 : 8 }}>
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
    </details>
  );
}

/** Every objection, as a scannable list of short rows with detail collapsed, plus the slots the published
 *  reports don't itemise — each one labelled, verbatim, "Not itemised in the published reports". */
export function ObjectionRows({
  objections, missing, checkedAll, identified, reportedTotal, reportHref,
}: {
  objections: EciObjection[];
  missing: number;
  checkedAll: boolean;
  identified: number;
  reportedTotal: number;
  reportHref: string | null;
}) {
  return (
    <div className="eci2-card" style={{ padding: "20px 24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 10, flexWrap: "wrap", marginBottom: 6 }}>
        <h2 className="serif" style={{ fontSize: 19, fontWeight: 650, margin: 0 }}>Every objection, in order</h2>
        <span className="mono" style={{ fontSize: 12, color: "var(--muted)", display: "inline-flex", alignItems: "center", gap: 10 }}>
          {identified} of {reportedTotal} identified
          {checkedAll && (
            <span style={{ display: "inline-flex", alignItems: "center", gap: 4, color: "var(--eci-check)" }}>
              <svg width="11" height="11" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                <path d="M2.5 6.2l2.2 2.2 4.8-5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              All checked against a citation
            </span>
          )}
        </span>
      </div>

      <div style={{ borderTop: "1px solid var(--rule)" }}>
        {objections.map((o) => (
          <ObjectionRow key={o.n} o={o} />
        ))}
        {Array.from({ length: missing }).map((_, i) => (
          <div key={`empty-${i}`} className="eci2-obj-empty">
            <span aria-hidden className="eci2-obj-empty-dots">
              <span />
              <span />
              <span />
            </span>
            <span style={{ fontSize: 13.5, fontWeight: 600, color: "var(--ink2)" }}>{EMPTY_SLOT_HEADING}</span>
          </div>
        ))}
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10, paddingTop: 12 }}>
        <span style={{ fontSize: 13, color: "var(--muted)" }}>
          Numbered by date in this record, not by the newspaper. The Indian Express counts {missing} more toward its
          total of {reportedTotal}, without a dated note to match.
        </span>
        {reportHref && (
          <Link href={reportHref} className="mono" style={{ fontSize: 13.5, color: "var(--accent-2)", textDecoration: "none" }}>
            Source: The Indian Express · Read the investigation →
          </Link>
        )}
      </div>
    </div>
  );
}
