import Link from "next/link";
import type { EciEntry } from "@/types/eci-files";
import { eciEntryHref, eciLaneLabel, formatEciDate } from "@/lib/eci-files";
import { StatusChip } from "@/components/eci-files/StatusChip";
import { CitationList } from "@/components/eci-files/CitationList";
import { PendingFlag } from "@/components/ui";

/** The drawer's content: title, date, status, attribution, summary, people, responses and citations
 *  (REDESIGN-SPEC §"Drawer"). Server-rendered — only the surrounding `EntryDrawer` shell is a client
 *  component, so this is fetched with the one entry this view actually needs, not the whole record.
 *  `preserve` is the page's current lane/topic/person/window, carried into any "replying to" / "responses"
 *  link so following one doesn't reset the timeline to its defaults. */
export function EntryDetail({ entry, preserve }: { entry: EciEntry; preserve?: Record<string, string | undefined> }) {
  return (
    <article>
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", marginBottom: 10 }}>
        <span className="mono" style={{ fontSize: 12, color: "var(--muted)" }}>{formatEciDate(entry.date, entry.date_precision)}</span>
        <StatusChip status={entry.status} />
        <span className="mono" style={{ fontSize: 9.5, letterSpacing: "0.06em", color: "var(--faint)" }}>{eciLaneLabel(entry.lane).toUpperCase()}</span>
        {entry.check_status === "unchecked" && <PendingFlag>NOT YET CHECKED</PendingFlag>}
      </div>

      <h2 className="serif" style={{ fontSize: 21, fontWeight: 600, lineHeight: 1.3, margin: "0 0 10px" }}>{entry.title}</h2>

      {entry.response_to && (
        <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 10 }}>
          Replying to{" "}
          <Link href={eciEntryHref(entry.response_to, preserve)} style={{ color: "var(--eci-ink)", textDecoration: "none" }}>
            entry {entry.response_to}
          </Link>
        </div>
      )}

      <p style={{ fontSize: 14, color: "var(--ink2)", lineHeight: 1.6, margin: "0 0 14px" }}>{entry.summary}</p>

      {entry.attributed_to && (entry.status === "claim" || entry.status === "response") && (
        <div style={{ fontSize: 12.5, color: "var(--muted)", marginBottom: 12 }}>
          Attributed to <strong style={{ color: "var(--ink2)", fontWeight: 500 }}>{entry.attributed_to}</strong>
        </div>
      )}

      {entry.people.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 14 }}>
          {entry.people.map((p) => (
            <Link
              key={p.slug}
              href={`/eci-files/people/${p.slug}`}
              className="mono"
              style={{ fontSize: 11, color: "var(--eci-ink)", textDecoration: "none", border: "1px solid var(--rule)", borderRadius: 20, padding: "3px 10px" }}
            >
              {p.name}
            </Link>
          ))}
        </div>
      )}

      {entry.responses.length > 0 && (
        <div style={{ margin: "0 0 14px", padding: "10px 12px", borderRadius: 8, background: "var(--sunken)" }}>
          <div className="mono" style={{ fontSize: 9.5, letterSpacing: "0.06em", color: "var(--faint)", marginBottom: 5 }}>
            RESPONSE{entry.responses.length > 1 ? "S" : ""}
          </div>
          {entry.responses.map((r) => (
            <div key={r.id} style={{ fontSize: 13 }}>
              <Link href={eciEntryHref(r.id, preserve)} style={{ color: "var(--ink)", textDecoration: "none" }}>{r.title}</Link>{" "}
              <span className="mono" style={{ fontSize: 10.5, color: "var(--muted)" }}>({r.date ?? "—"})</span>
            </div>
          ))}
        </div>
      )}

      {entry.notes && (
        <p style={{ fontSize: 12.5, color: "var(--muted)", fontStyle: "italic", margin: "0 0 14px" }}>{entry.notes}</p>
      )}

      <div className="mono" style={{ fontSize: 9.5, letterSpacing: "0.06em", color: "var(--faint)", marginBottom: 6 }}>SOURCES</div>
      <CitationList citations={entry.citations} />
    </article>
  );
}
