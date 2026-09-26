import Link from "next/link";
import type { EciPersonGroup, EciPhoto } from "@/types/eci-files";
import { personGroupMeta, photoCredit } from "@/lib/eci-files";
import { PersonAvatar } from "@/components/eci-files/PersonAvatar";

/** The top of `/eci-files/people/[slug]` (PHASE4-SPEC.md §2.1): avatar, photo credit, name, role, a group
 *  + serving/former chip row, the service line, and the breadcrumb. `showStatusChip` is false for the
 *  `named` group, which has no tenure to be "serving" or "former" in. */
export function ProfileHeader({
  name, photo, role, service, group, current, showStatusChip = true,
}: {
  name: string;
  photo: EciPhoto | null;
  role: string | null;
  service: string | null;
  group: EciPersonGroup;
  current: boolean;
  showStatusChip?: boolean;
}) {
  const meta = personGroupMeta(group);
  return (
    <header style={{ marginBottom: 20 }}>
      <div style={{ marginBottom: 12 }}>
        <Link href="/eci-files/people" className="mono" style={{ fontSize: 12, color: "var(--muted)", textDecoration: "none" }}>← People</Link>
      </div>

      <div className="eci-avatar-lg"><PersonAvatar name={name} photo={photo} size={112} /></div>
      <div className="eci-avatar-sm"><PersonAvatar name={name} photo={photo} size={72} /></div>

      {photo && (
        <div style={{ marginTop: 8, fontSize: 10.5, color: "var(--faint)" }} title={photo.attribution}>
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

      <h1 className="serif" style={{ fontSize: "clamp(26px, 4vw, 34px)", fontWeight: 600, margin: "12px 0 4px", lineHeight: 1.15 }}>{name}</h1>
      {role && <p style={{ fontSize: 14.5, color: "var(--ink2)", margin: "0 0 10px" }}>{role}</p>}

      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 10 }}>
        <span
          className="mono"
          style={{ fontSize: 10.5, fontWeight: 600, letterSpacing: "0.04em", padding: "3px 10px", borderRadius: 20, background: "var(--sunken)", color: "var(--ink2)" }}
        >
          {meta.chip.toUpperCase()}
        </span>
        {showStatusChip && (
          <span
            className="mono"
            style={{
              fontSize: 10.5, fontWeight: 600, letterSpacing: "0.04em", padding: "3px 10px", borderRadius: 20,
              ...(current
                ? { background: "color-mix(in srgb, var(--eci-ink) 12%, var(--card2))", color: "var(--eci-ink)" }
                : { background: "var(--sunken)", color: "var(--muted)" }),
            }}
          >
            {current ? "SERVING" : "FORMER"}
          </span>
        )}
      </div>

      {service && <p style={{ fontSize: 13, color: "var(--muted)", margin: 0, maxWidth: "72ch" }}>{service}</p>}
    </header>
  );
}
