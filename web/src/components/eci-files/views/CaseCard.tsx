import Link from "next/link";
import type { EciCaseSummary } from "@/types/eci-files";
import { ECI_CASE_STATUS_LABEL, formatEciDate } from "@/lib/eci-files";

/** One card on `/eci-files/courts` — the case's shape at a glance, before the reader opens its full
 *  order-by-order page (PHASE5-SPEC §6.5). */
export function CaseCard({ c }: { c: EciCaseSummary }) {
  return (
    <Link href={`/eci-files/courts/${c.slug}`} className="eci-case-card lift">
      <h2 className="serif" style={{ fontSize: 16.5, fontWeight: 600, margin: 0 }}>{c.short_name}</h2>
      <div style={{ fontSize: 12.5, color: "var(--ink2)" }}>{c.title}</div>
      {c.case_number && <div className="mono" style={{ fontSize: 11, color: "var(--muted)", overflowWrap: "anywhere" }}>{c.case_number}</div>}
      <div style={{ fontSize: 12, color: "var(--muted)" }}>{c.court}</div>
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", margin: "4px 0" }}>
        <span
          className="mono"
          style={{ fontSize: 10.5, fontWeight: 600, padding: "3px 9px", borderRadius: 999, border: "1px solid var(--border2)", color: "var(--ink2)", background: "var(--sunken)" }}
        >
          {ECI_CASE_STATUS_LABEL[c.short_status]}
        </span>
        {c.status_note && <span style={{ fontSize: 12, color: "var(--muted)" }}>{c.status_note}</span>}
      </div>
      <div className="mono" style={{ fontSize: 11, color: "var(--faint)" }}>
        {c.item_count} recorded steps · {c.order_count} orders and judgments
      </div>
      {c.latest && (
        <div style={{ fontSize: 12, color: "var(--ink2)", marginTop: 4 }}>
          Latest: {formatEciDate(c.latest.date, c.latest.date_precision)} · {c.latest.title}
        </div>
      )}
    </Link>
  );
}
