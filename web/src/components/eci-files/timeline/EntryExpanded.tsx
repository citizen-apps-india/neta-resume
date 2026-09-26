"use client";

import { useState, type CSSProperties } from "react";
import Link from "next/link";
import type { EciEntryDetail } from "@/types/eci-files";
import { formatEciDate, ECI_TEXT_STATUS_SHORT } from "@/lib/eci-files";
import { LaneChip } from "@/components/eci-files/ui/LaneChip";
import { StatusWord } from "@/components/eci-files/ui/StatusWord";
import { CitationList } from "@/components/eci-files/CitationList";
import { RoleChip } from "@/components/eci-files/views/RoleChip";
import { LinkifiedNote } from "@/components/eci-files/views/LinkifiedNote";

/** The entry that opens IN PLACE (DESIGN-BRIEF: replacing the overlay drawer): summary, case/context
 *  link, sources, Previous/Next and Copy link, drawn as an elevated card in the same spot the row was. */
export function EntryExpanded({
  entry, isKeyMoment, onOpenEntry, onCollapse, onPrev, onNext, canPrev, canNext, shareUrl,
}: {
  entry: EciEntryDetail;
  isKeyMoment: boolean;
  onOpenEntry: (id: string) => void;
  onCollapse: () => void;
  onPrev: () => void;
  onNext: () => void;
  canPrev: boolean;
  canNext: boolean;
  shareUrl: string;
}) {
  const [copied, setCopied] = useState(false);
  const ctx = entry.context;

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      // clipboard access can be denied (permissions, insecure context) — the link is still in the address bar
    }
  }

  return (
    <div
      id={`eci-entry-${entry.id}`}
      style={{
        display: "flex", flexDirection: "column", gap: 12, background: "var(--card)", border: "1px solid var(--border)",
        borderRadius: 14, padding: "20px 22px", boxShadow: "0 8px 28px -18px rgba(18,19,23,0.35)",
      }}
    >
      <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap", justifyContent: "space-between" }}>
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <LaneChip lane={entry.lane} />
          {isKeyMoment && (
            <span className="mono" style={{ fontSize: 10.5, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--eci-ink)" }}>
              Key moment
            </span>
          )}
        </div>
        <button
          type="button"
          aria-label="Collapse entry"
          onClick={onCollapse}
          className="tap"
          style={{ minHeight: 40, minWidth: 40, borderRadius: 10, border: "1px solid var(--border)", background: "var(--card2)", cursor: "pointer", color: "var(--ink2)" }}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
            <path d="M3.5 8.5L7 5l3.5 3.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>

      <div className="mono" style={{ fontSize: 12.5, color: "var(--muted)" }}>{formatEciDate(entry.date, entry.date_precision)}</div>
      <h4 style={{ margin: 0, fontSize: 22, fontWeight: 650, lineHeight: 1.25 }}>{entry.title}</h4>
      <p style={{ margin: 0, fontSize: 15, lineHeight: 1.6, color: "var(--ink2)", maxWidth: "62ch" }}>{entry.summary}</p>

      {entry.attributed_to && (entry.status === "claim" || entry.status === "response") && (
        <div style={{ fontSize: 12.5, color: "var(--muted)" }}>
          Attributed to <strong style={{ color: "var(--ink2)", fontWeight: 500 }}>{entry.attributed_to}</strong>
        </div>
      )}

      {entry.response_to && (
        <div style={{ fontSize: 12.5, color: "var(--muted)" }}>
          Replying to{" "}
          <button type="button" onClick={() => onOpenEntry(entry.response_to!)} className="mono" style={{ border: 0, background: "none", padding: 0, color: "var(--eci-ink)", cursor: "pointer", font: "inherit" }}>
            entry {entry.response_to}
          </button>
        </div>
      )}

      {entry.people.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {entry.people.map((p) => (
            <Link key={p.slug} href={`/eci-files/people/${p.slug}`} className="mono" style={{ fontSize: 11, color: "var(--eci-ink)", textDecoration: "none", border: "1px solid var(--rule)", borderRadius: 20, padding: "3px 10px" }}>
              {p.name}
            </Link>
          ))}
        </div>
      )}

      <div style={{ display: "flex", gap: 14, alignItems: "center", flexWrap: "wrap" }}>
        <StatusWord status={entry.status} checked={entry.check_status === "checked"} />
        {ctx?.case && (
          <span style={{ fontSize: 13, color: "var(--ink2)", display: "inline-flex", gap: 8, alignItems: "center" }}>
            Part of <Link href={`/eci-files/courts/${ctx.case.slug}`} style={{ color: "var(--eci-ink)", textDecoration: "none" }}>{ctx.case.short_name}</Link>
            <RoleChip role={ctx.case.role} />
          </span>
        )}
      </div>

      {entry.responses.length > 0 && (
        <div style={{ padding: "10px 12px", borderRadius: 8, background: "var(--sunken)" }}>
          <div className="mono" style={{ fontSize: 9.5, letterSpacing: "0.06em", color: "var(--faint)", marginBottom: 5 }}>
            RESPONSE{entry.responses.length > 1 ? "S" : ""}
          </div>
          {entry.responses.map((r) => (
            <div key={r.id} style={{ fontSize: 13 }}>
              <button type="button" onClick={() => onOpenEntry(r.id)} style={{ border: 0, background: "none", padding: 0, color: "var(--ink)", cursor: "pointer", font: "inherit", textAlign: "left" }}>
                {r.title}
              </button>{" "}
              <span className="mono" style={{ fontSize: 10.5, color: "var(--muted)" }}>({r.date ?? "—"})</span>
            </div>
          ))}
        </div>
      )}

      {entry.notes && (
        <p style={{ fontSize: 12.5, color: "var(--muted)", fontStyle: "italic", margin: 0 }}>
          <LinkifiedNote text={entry.notes} basePath="/eci-files/timeline" />
        </p>
      )}

      {ctx && ctx.objections.length > 0 && (
        <div style={{ fontSize: 12.5 }}>
          {ctx.objections.map((o) => (
            <Link key={o.n} href={`/eci-files/objections#objection-${o.n}`} style={{ color: "var(--eci-ink)", textDecoration: "none" }}>
              Objection {o.n} →
            </Link>
          ))}
        </div>
      )}

      {ctx && ctx.rule_diffs.length > 0 && (
        <div style={{ fontSize: 12.5, display: "flex", flexDirection: "column", gap: 4 }}>
          {ctx.rule_diffs.map((d) => (
            <div key={d.id}>
              <Link href={`/eci-files/rules/${d.id}`} style={{ color: "var(--eci-ink)", textDecoration: "none" }}>Before and after: {d.title} →</Link>{" "}
              <span className="mono" style={{ fontSize: 10, color: "var(--faint)" }}>{ECI_TEXT_STATUS_SHORT[d.text_status]}</span>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 6, paddingTop: 10, borderTop: "1px solid var(--rule2)" }}>
        <span className="mono" style={{ fontSize: 10.5, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--faint)" }}>
          Source{entry.citations.length === 1 ? "" : "s"}
        </span>
        <CitationList citations={entry.citations} />
      </div>

      <div style={{ display: "flex", gap: 10, alignItems: "center", paddingTop: 4, flexWrap: "wrap" }}>
        <button type="button" onClick={onPrev} disabled={!canPrev} className="btnGhost" style={navBtnStyle}>← Previous</button>
        <button type="button" onClick={onNext} disabled={!canNext} className="btnGhost" style={navBtnStyle}>Next →</button>
        <span style={{ flexGrow: 1 }} />
        <button type="button" onClick={copyLink} style={{ minHeight: 40, padding: "0 14px", borderRadius: 10, border: 0, background: "none", fontSize: 13.5, color: "var(--eci-ink)", cursor: "pointer" }}>
          {copied ? "Copied" : "Copy link"}
        </button>
        <span aria-live="polite" style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)" }}>
          {copied ? "Link copied" : ""}
        </span>
      </div>
    </div>
  );
}

const navBtnStyle: CSSProperties = {
  minHeight: 40, padding: "0 14px", borderRadius: 10, border: "1px solid var(--border)", background: "var(--card2)", fontSize: 13.5, cursor: "pointer", color: "var(--ink)",
};
