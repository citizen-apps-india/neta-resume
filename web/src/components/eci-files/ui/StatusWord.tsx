import type { EciEntryStatus } from "@/types/eci-files";

const LABEL: Record<EciEntryStatus, string> = { documented: "Document", reported: "Reported", claim: "Claim", response: "Response" };

/** How an entry is sourced, as a word, and whether a fact-checker has opened its sources. */
export function StatusWord({ status, checked }: { status: EciEntryStatus; checked: boolean }) {
  return (
    <span className="mono" style={{ display: "inline-flex", gap: 10, alignItems: "center", fontSize: 11, letterSpacing: "0.02em", color: "var(--ink2)" }}>
      <span style={{ padding: "2px 7px", border: "1px solid var(--border)", borderRadius: 4 }}>{LABEL[status]}</span>
      {checked ? (
        <span style={{ display: "inline-flex", alignItems: "center", gap: 4, color: "var(--eci-check)" }}>
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M2.5 6.2l2.2 2.2 4.8-5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" /></svg>
          Checked
        </span>
      ) : (
        <span style={{ color: "var(--muted)" }}>Not yet checked</span>
      )}
    </span>
  );
}
