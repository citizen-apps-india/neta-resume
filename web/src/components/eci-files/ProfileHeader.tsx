import Link from "next/link";
import type { ReactNode } from "react";
import type { EciPersonGroup, EciPhoto } from "@/types/eci-files";
import { personGroupMeta, photoCredit } from "@/lib/eci-files";
import { PersonAvatar } from "@/components/eci-files/PersonAvatar";

/** The top of `/eci-files/people/[slug]` (C-After-Profile.dc.html): breadcrumb, then one bordered hero
 *  card holding the identity row (avatar, photo credit, name, role, group + serving/former chip) and
 *  whatever the page passes as `children` — the career line and the key-facts tiles — so "identity + one
 *  horizontal career line" reads as a single visual unit instead of stacked sections. `showStatusChip` is
 *  false for the `named` group, which has no tenure to be "serving" or "former" in. */
export function ProfileHeader({
  name, photo, role, service, group, current, showStatusChip = true, children,
}: {
  name: string;
  photo: EciPhoto | null;
  role: string | null;
  service: string | null;
  group: EciPersonGroup;
  current: boolean;
  showStatusChip?: boolean;
  children?: ReactNode;
}) {
  const meta = personGroupMeta(group);
  return (
    <header style={{ marginBottom: 24 }}>
      <div style={{ marginBottom: 12 }}>
        <Link href="/eci-files/people" className="mono" style={{ fontSize: 12, color: "var(--muted)", textDecoration: "none" }}>← People</Link>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 18, border: "1px solid var(--rule)", borderRadius: 14, background: "var(--card)", padding: "24px clamp(16px,3vw,26px)" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
            <div className="eci-avatar-lg"><PersonAvatar name={name} photo={photo} size={64} /></div>
            <div className="eci-avatar-sm"><PersonAvatar name={name} photo={photo} size={52} /></div>

            <div style={{ display: "flex", flexDirection: "column", gap: 4, minWidth: 0 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                <h1 className="serif" style={{ fontSize: "clamp(24px, 4vw, 30px)", fontWeight: 700, margin: 0, lineHeight: 1.15 }}>{name}</h1>
                {showStatusChip && (
                  <span
                    className="mono"
                    style={{
                      fontSize: 10.5, fontWeight: 600, letterSpacing: "0.04em", padding: "2px 8px", borderRadius: 999,
                      ...(current
                        ? { color: "var(--eci-ink)", border: "1px solid var(--eci-ink)" }
                        : { color: "var(--muted)", border: "1px solid var(--border)" }),
                    }}
                  >
                    {current ? "SERVING" : "FORMER"}
                  </span>
                )}
                <span
                  className="mono"
                  style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.04em", padding: "2px 8px", borderRadius: 999, background: "var(--sunken)", color: "var(--ink2)" }}
                >
                  {meta.chip.toUpperCase()}
                </span>
              </div>
              {(role || service) && (
                <span style={{ fontSize: 14.5, color: "var(--ink2)" }}>
                  {role}{role && service ? " · " : ""}{service}
                </span>
              )}
            </div>
          </div>

          {photo && (
            <div style={{ fontSize: 10.5, color: "var(--faint)" }} title={photo.attribution}>
              Photo:{" "}
              <a href={photo.source_page} target="_blank" rel="noopener noreferrer" style={{ color: "var(--faint)" }}>
                {photoCredit(photo)}
              </a>{" "}
              ·{" "}
              <a href={photo.licence_url} target="_blank" rel="noopener noreferrer" style={{ color: "var(--faint)" }}>
                GODL-India
              </a>
            </div>
          )}
        </div>

        {children}
      </div>
    </header>
  );
}
