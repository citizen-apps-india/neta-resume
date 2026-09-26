import type { EciPhoto } from "@/types/eci-files";
import { initials } from "@/lib/eci-files";

/** Minimal local stand-in for phase 4's `PersonAvatar` (docs/eci-files/PHASE5-SPEC.md §0: "From phase 4:
 *  PersonAvatar({name, photo, size, decorative})"). Phase 4 hadn't landed on this branch when phase 5
 *  started, so this lives under `views/` rather than the shared `components/eci-files/` root, with the
 *  same prop shape, so a rebase can delete this file and repoint imports at phase 4's version without
 *  touching any call site's props. Renders a photo when the licence is confirmed (PHASES-3-5-DECISIONS.md:
 *  "the five reviewer-confirmed Commons photos"), initials otherwise, at the same size and frame either
 *  way — "the UI must look deliberate either way". */
export function PersonAvatar({
  name, photo, size = 28, decorative = false,
}: {
  name: string;
  photo?: EciPhoto | null;
  size?: number;
  decorative?: boolean;
}) {
  const common: React.CSSProperties = {
    width: size, height: size, borderRadius: "50%", flexShrink: 0,
    border: "1px solid var(--rule)", overflow: "hidden",
    display: "inline-flex", alignItems: "center", justifyContent: "center",
  };
  if (photo?.url) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={photo.url}
        alt={decorative ? "" : name}
        width={size}
        height={size}
        loading="lazy"
        style={{ ...common, objectFit: "cover", background: "var(--photo-b)" }}
      />
    );
  }
  return (
    <span
      className="mono"
      role={decorative ? "presentation" : undefined}
      aria-hidden={decorative || undefined}
      aria-label={decorative ? undefined : name}
      style={{
        ...common, background: "var(--sunken)", color: "var(--muted)",
        fontSize: Math.max(9, size * 0.36), fontWeight: 600,
      }}
    >
      {initials(name)}
    </span>
  );
}
