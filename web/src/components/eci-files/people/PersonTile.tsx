import Link from "next/link";
import type { EciPersonSummary } from "@/types/eci-files";
import { PersonAvatar } from "@/components/eci-files/PersonAvatar";

/** A compact avatar-grid tile for `/eci-files/people` (C-After-People.dc.html): avatar at the row start,
 *  name, role and a Serving/Former tag — nothing else. Two sizes share one shape so a row of commissioners
 *  never reads as a judgment about the people shown smaller: `size="commission"` (40px avatar, room for a
 *  "Serving"/"Former" tag) for the Commission group, `size="compact"` (30px avatar, role only) for the
 *  Senior officials and State CEO grids, which have no serving/former distinction worth a tag. */
export function PersonTile({
  p, size = "commission", roleOverride,
}: {
  p: EciPersonSummary;
  size?: "commission" | "compact";
  roleOverride?: string;
}) {
  const avatarSize = size === "commission" ? 40 : 30;
  const hasDates = p.tenure.some((t) => t.from || t.to);
  return (
    <Link
      href={`/eci-files/people/${p.slug}`}
      className="lift"
      style={{
        display: "flex", alignItems: "center", gap: size === "commission" ? 12 : 8, textDecoration: "none", color: "var(--ink)",
        border: "1px solid var(--rule)", borderRadius: size === "commission" ? 12 : 10, background: "var(--card)",
        padding: size === "commission" ? "12px 14px" : "8px 10px", minWidth: 0,
      }}
    >
      <PersonAvatar name={p.name} photo={p.photo} size={avatarSize} decorative />
      <div style={{ display: "flex", flexDirection: "column", gap: 1, minWidth: 0, flex: 1 }}>
        <span
          style={{
            fontSize: size === "commission" ? 14 : 12.5, fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
          }}
        >
          {p.name}
        </span>
        <span style={{ fontSize: size === "commission" ? 11.5 : 10.5, color: "var(--muted)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
          {roleOverride ?? p.role ?? "—"}
        </span>
      </div>
      {size === "commission" && hasDates && (
        <span
          className="mono"
          style={{
            flexShrink: 0, fontSize: 9, fontWeight: 600, letterSpacing: "0.04em", padding: "2px 8px", borderRadius: 999,
            ...(p.current
              ? { color: "var(--eci-ink)", border: "1px solid var(--eci-ink)" }
              : { color: "var(--faint)", border: "1px solid transparent" }),
          }}
        >
          {p.current ? "SERVING" : "FORMER"}
        </span>
      )}
    </Link>
  );
}
