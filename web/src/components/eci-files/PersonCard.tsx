import Link from "next/link";
import type { EciPersonSummary } from "@/types/eci-files";
import { formatTenure } from "@/lib/eci-files";
import { PersonAvatar } from "@/components/eci-files/PersonAvatar";
import { TenureBar } from "@/components/eci-files/TenureBar";
import { EntryCountLine } from "@/components/eci-files/StatusCountBar";

/** A card on `/eci-files/people` for the `commission` and `secretariat` groups (PHASE4-SPEC.md §1.3). The
 *  whole card is one link. Commission cards show the shared tenure axis as a bar; secretariat cards show
 *  the tenure text instead — the bar reads best at commission scale (nine rows share one axis), less well
 *  as a full row of forty. */
export function PersonCard({ p, variant = "commission" }: { p: EciPersonSummary; variant?: "commission" | "secretariat" }) {
  const avatarSize = variant === "commission" ? 64 : 48;
  const hasDates = p.tenure.some((t) => t.from || t.to);
  const total = p.status_counts.documented + p.status_counts.reported + p.status_counts.claim + p.status_counts.response;

  return (
    <Link
      href={`/eci-files/people/${p.slug}`}
      className="lift"
      style={{
        display: "flex", flexDirection: "column", gap: 10, textDecoration: "none", color: "var(--ink)",
        border: "1px solid var(--rule)", borderRadius: 12, background: "var(--card2)", padding: "16px 18px",
      }}
    >
      <div style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
        <PersonAvatar name={p.name} photo={p.photo} size={avatarSize} decorative />
        <div style={{ minWidth: 0, flex: 1 }}>
          <div className="serif" style={{ fontSize: 17, fontWeight: 600, lineHeight: 1.25 }}>{p.name}</div>
          <div style={{ fontSize: 12.5, color: "var(--ink2)", marginTop: 2 }}>{p.role ?? "—"}</div>
          {hasDates && (
            <span
              className="mono"
              style={{
                display: "inline-block", marginTop: 6, fontSize: 10, fontWeight: 600, letterSpacing: "0.04em",
                padding: "2px 8px", borderRadius: 20,
                ...(p.current
                  ? { background: "color-mix(in srgb, var(--eci-ink) 12%, var(--card2))", color: "var(--eci-ink)" }
                  : { background: "var(--sunken)", color: "var(--muted)" }),
              }}
            >
              {p.current ? "SERVING" : "FORMER"}
            </span>
          )}
        </div>
      </div>

      {variant === "commission" ? (
        <TenureBar tenure={p.tenure} height={8} />
      ) : (
        <div style={{ fontSize: 11.5, color: "var(--muted)" }}>
          {hasDates ? formatTenure(p.tenure).join(" · ") : "Dates not on record"}
        </div>
      )}

      <EntryCountLine counts={p.status_counts} total={total} />

      {p.service && (
        <div
          title={p.service}
          style={{ fontSize: 11.5, color: "var(--muted)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}
        >
          {p.service}
        </div>
      )}
    </Link>
  );
}
