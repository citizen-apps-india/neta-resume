import Link from "next/link";
import type { EciEntry } from "@/types/eci-files";
import { eciEntryHref, eciLaneLabel, formatEciDate } from "@/lib/eci-files";
import { StatusChip } from "@/components/eci-files/StatusChip";
import { CitationList } from "@/components/eci-files/CitationList";
import { PendingFlag } from "@/components/ui";
// ECI Files phase 5: the context block below (§6.1's "EntryDetail gains a context block").
import type { EciEntryContext } from "@/types/eci-files";
import { eciEntryHrefIn, ECI_TEXT_STATUS_SHORT } from "@/lib/eci-files";
import { RoleChip } from "@/components/eci-files/views/RoleChip";

const ECI_OBJECTION_TOTAL = 14;

/** The drawer's content: title, date, status, attribution, summary, people, responses and citations
 *  (REDESIGN-SPEC §"Drawer"). Server-rendered — only the surrounding `EntryDrawer` shell is a client
 *  component, so this is fetched with the one entry this view actually needs, not the whole record.
 *  `preserve` is the page's current lane/topic/person/window, carried into any "replying to" / "responses"
 *  link so following one doesn't reset the timeline to its defaults. `basePath` is the page the drawer is
 *  open on (a profile, /answers, a case page), so entry links stay there. `entry.context` (phase 5) is
 *  optional: a plain `EciEntry` renders nothing new. */
export function EntryDetail({
  entry, preserve, basePath = "/eci-files/timeline",
}: {
  entry: EciEntry & { context?: EciEntryContext };
  preserve?: Record<string, string | undefined>;
  basePath?: string;
}) {
  const ctx = entry.context;
  const linkBase = basePath;
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
          <Link href={eciEntryHref(entry.response_to, preserve, basePath)} style={{ color: "var(--eci-ink)", textDecoration: "none" }}>
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
              <Link href={eciEntryHref(r.id, preserve, basePath)} style={{ color: "var(--ink)", textDecoration: "none" }}>{r.title}</Link>{" "}
              <span className="mono" style={{ fontSize: 10.5, color: "var(--muted)" }}>({r.date ?? "—"})</span>
            </div>
          ))}
        </div>
      )}

      {entry.notes && (
        <p style={{ fontSize: 12.5, color: "var(--muted)", fontStyle: "italic", margin: "0 0 14px" }}>{entry.notes}</p>
      )}

      {/* --- ECI Files phase 5 (views): charge/answer, case and objection/diff context --- */}
      {ctx && ctx.pairs.length > 0 && ctx.pairs.map((pair) => (
        <div
          key={pair.charge.id}
          style={{ margin: "0 0 14px", padding: "10px 12px", borderRadius: 8, border: "1px solid var(--rule)", background: "var(--card2)" }}
        >
          <div className="mono" style={{ fontSize: 9.5, letterSpacing: "0.06em", color: "var(--faint)", marginBottom: 6 }}>CHARGE AND ANSWER</div>
          <div style={{ fontSize: 12.5, marginBottom: 6 }}>
            <span style={{ color: "var(--muted)" }}>Charge: </span>
            {pair.role === "charge" ? (
              <strong style={{ color: "var(--ink)", fontWeight: 600 }}>This entry</strong>
            ) : (
              <Link href={eciEntryHrefIn(linkBase, pair.charge.id, preserve)} style={{ color: "var(--eci-ink)", textDecoration: "none" }}>
                {pair.charge.title}
              </Link>
            )}
          </div>
          <div style={{ fontSize: 12.5, marginBottom: 6 }}>
            <span style={{ color: "var(--muted)" }}>Responses: </span>
            {pair.responses.length === 0 ? (
              <span style={{ color: "var(--muted)" }}>No response on record.</span>
            ) : (
              pair.responses.map((r, i) => (
                <span key={r.id}>
                  {i > 0 && ", "}
                  <Link href={eciEntryHrefIn(linkBase, r.id, preserve)} style={{ color: "var(--eci-ink)", textDecoration: "none" }}>{r.title}</Link>
                </span>
              ))
            )}
          </div>
          {pair.record.length > 0 && (
            <div style={{ fontSize: 12.5, marginBottom: 6 }}>
              <span style={{ color: "var(--muted)" }}>What the record shows: </span>
              {pair.record.map((r, i) => (
                <span key={r.id}>
                  {i > 0 && ", "}
                  <Link href={eciEntryHrefIn(linkBase, r.id, preserve)} style={{ color: "var(--eci-ink)", textDecoration: "none" }}>{r.title}</Link>
                </span>
              ))}
            </div>
          )}
          {pair.note && <p style={{ fontSize: 12, color: "var(--muted)", fontStyle: "italic", margin: "0 0 8px" }}>{pair.note}</p>}
          <Link href={`/eci-files/answers#charge-${pair.charge.id}`} className="mono" style={{ fontSize: 11, color: "var(--accent-2)", textDecoration: "none" }}>
            See all charges and answers →
          </Link>
        </div>
      ))}

      {ctx?.case && (
        <div style={{ fontSize: 12.5, marginBottom: 14, display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <RoleChip role={ctx.case.role} />
          <Link href={`/eci-files/courts/${ctx.case.slug}`} style={{ color: "var(--eci-ink)", textDecoration: "none" }}>
            Part of the case: {ctx.case.short_name} →
          </Link>
        </div>
      )}

      {ctx && ctx.objections.length > 0 && (
        <div style={{ fontSize: 12.5, marginBottom: 8 }}>
          {ctx.objections.map((o) => (
            <div key={o.n}>
              <Link href={`/eci-files/objections#objection-${o.n}`} style={{ color: "var(--eci-ink)", textDecoration: "none" }}>
                Objection {o.n} of {ECI_OBJECTION_TOTAL} →
              </Link>
            </div>
          ))}
        </div>
      )}

      {ctx && ctx.rule_diffs.length > 0 && (
        <div style={{ fontSize: 12.5, marginBottom: 14 }}>
          {ctx.rule_diffs.map((d) => (
            <div key={d.id}>
              <Link href={`/eci-files/rules/${d.id}`} style={{ color: "var(--eci-ink)", textDecoration: "none" }}>
                Before and after: {d.title} →
              </Link>{" "}
              <span className="mono" style={{ fontSize: 10, color: "var(--faint)" }}>{ECI_TEXT_STATUS_SHORT[d.text_status]}</span>
            </div>
          ))}
        </div>
      )}

      <div className="mono" style={{ fontSize: 9.5, letterSpacing: "0.06em", color: "var(--faint)", marginBottom: 6 }}>SOURCES</div>
      <CitationList citations={entry.citations} />
    </article>
  );
}
