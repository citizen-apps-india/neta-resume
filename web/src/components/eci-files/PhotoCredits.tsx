import type { EciPhoto } from "@/types/eci-files";

/** The people page's photo-credits footnote (PHASE4-SPEC.md §4.3): every photo's attribution line, linked
 *  to its source and licence, plus the one-line note that everyone else is shown with initials. Cards and
 *  avatars under 64px carry no caption of their own — this footnote is where their credit lives. */
export function PhotoCredits({ photos }: { photos: { slug: string; name: string; photo: EciPhoto }[] }) {
  if (photos.length === 0) return null;
  return (
    <details className="eci-more" style={{ marginTop: 26 }}>
      <summary className="mono" style={{ fontSize: 12, color: "var(--accent-2)", cursor: "pointer" }}>Photo credits</summary>
      <ul style={{ listStyle: "none", margin: "10px 0 0", padding: 0, display: "flex", flexDirection: "column", gap: 6 }}>
        {photos.map(({ slug, name, photo }) => (
          <li key={slug} style={{ fontSize: 12, color: "var(--muted)" }}>
            <strong style={{ color: "var(--ink2)", fontWeight: 500 }}>{name}:</strong>{" "}
            {photo.attribution}{" "}
            <a href={photo.source_page} target="_blank" rel="noopener noreferrer" style={{ color: "var(--accent-2)" }}>source ↗</a>{" "}
            <a href={photo.licence_url} target="_blank" rel="noopener noreferrer" style={{ color: "var(--accent-2)" }}>licence ↗</a>
          </li>
        ))}
      </ul>
      <p style={{ fontSize: 12, color: "var(--muted)", marginTop: 8 }}>People without a photo are shown with initials.</p>
    </details>
  );
}
