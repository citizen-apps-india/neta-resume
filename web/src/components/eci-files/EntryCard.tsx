import Link from "next/link";
import type { EciEntry } from "@/types/eci-files";
import { formatEciDate, titleOf } from "@/lib/eci-files";
import { StatusChip } from "@/components/eci-files/StatusChip";
import { CitationList } from "@/components/eci-files/CitationList";
import { PendingFlag } from "@/components/ui";

/** One record: date, title, summary, status chip, people, responses (beside the charge), citations.
 *  A response entry renders indented and captioned with what it answers. `allEntries` is the full list
 *  currently on the page, used only to resolve a response's parent title for that caption. */
export function EntryCard({ entry, allEntries }: { entry: EciEntry; allEntries: EciEntry[] }) {
  const isResponse = entry.status === "response";
  const replyingTo = isResponse ? titleOf(allEntries, entry.response_to) : null;

  return (
    <article
      id={`entry-${entry.id}`}
      style={{
        padding: "14px 0", borderTop: "1px solid var(--rule2)",
        marginLeft: isResponse ? 22 : 0,
        borderLeft: isResponse ? "2px solid var(--accent-soft-bd)" : "none",
        paddingLeft: isResponse ? 14 : 0,
      }}
    >
      <div style={{ display: "flex", alignItems: "baseline", gap: 10, flexWrap: "wrap", marginBottom: 5 }}>
        <span className="mono" style={{ fontSize: 11.5, color: "var(--muted)", whiteSpace: "nowrap" }}>
          {formatEciDate(entry.date, entry.date_precision)}
        </span>
        <StatusChip status={entry.status} />
        {entry.check_status === "unchecked" && <PendingFlag>NOT YET CHECKED</PendingFlag>}
      </div>

      <h3 className="serif" style={{ fontSize: 16.5, fontWeight: 600, margin: "0 0 5px", lineHeight: 1.3 }}>
        {entry.title}
      </h3>

      {isResponse && (
        <div style={{ fontSize: 11.5, color: "var(--muted)", marginBottom: 6 }}>
          Replying to{" "}
          {replyingTo ? (
            <a href={`#entry-${entry.response_to}`} style={{ color: "var(--accent-2)", textDecoration: "none" }}>
              {replyingTo}
            </a>
          ) : (
            "—"
          )}
        </div>
      )}

      <p style={{ fontSize: 13.5, color: "var(--ink2)", lineHeight: 1.55, margin: "0 0 8px", maxWidth: "72ch" }}>
        {entry.summary}
      </p>

      {entry.attributed_to && (entry.status === "claim" || entry.status === "response") && (
        <div style={{ fontSize: 11.5, color: "var(--muted)", marginBottom: 8 }}>
          Attributed to <strong style={{ color: "var(--ink2)", fontWeight: 500 }}>{entry.attributed_to}</strong>
        </div>
      )}

      {entry.people.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 8 }}>
          {entry.people.map((p) => (
            <Link
              key={p.slug}
              href={`/eci-files/people/${p.slug}`}
              className="mono"
              style={{ fontSize: 11, color: "var(--accent-2)", textDecoration: "none", border: "1px solid var(--rule)", borderRadius: 20, padding: "3px 10px" }}
            >
              {p.name}
            </Link>
          ))}
        </div>
      )}

      {entry.responses.length > 0 && (
        <div style={{ margin: "0 0 8px", padding: "8px 10px", borderRadius: 8, background: "var(--sunken)" }}>
          <div className="mono" style={{ fontSize: 9.5, letterSpacing: "0.06em", color: "var(--faint)", marginBottom: 4 }}>
            RESPONSE{entry.responses.length > 1 ? "S" : ""}
          </div>
          {entry.responses.map((r) => (
            <div key={r.id} style={{ fontSize: 12.5 }}>
              <a href={`#entry-${r.id}`} style={{ color: "var(--ink)", textDecoration: "none" }}>{r.title}</a>{" "}
              <span className="mono" style={{ fontSize: 10.5, color: "var(--muted)" }}>({r.date ?? "—"})</span>
            </div>
          ))}
        </div>
      )}

      {entry.notes && (
        <p style={{ fontSize: 12, color: "var(--muted)", fontStyle: "italic", margin: "0 0 8px", maxWidth: "72ch" }}>
          {entry.notes}
        </p>
      )}

      <CitationList citations={entry.citations} />
    </article>
  );
}
