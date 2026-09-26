/** The anchor-chip nav at the top of `/eci-files/people` and each profile — only the sections that exist
 *  on the page, each with a count (PHASE4-SPEC.md §1.1, §2.1). A section with a count of `undefined`
 *  (e.g. "Selected by") renders its label alone. */
export function SectionNav({
  items, ariaLabel,
}: {
  items: { id: string; label: string; count?: number }[];
  ariaLabel: string;
}) {
  if (items.length === 0) return null;
  return (
    <nav aria-label={ariaLabel} className="eci-section-nav" style={{ margin: "16px 0 28px" }}>
      {items.map((it) => (
        <a key={it.id} href={`#${it.id}`}>
          {it.label}
          {typeof it.count === "number" && (
            <span className="mono" style={{ color: "var(--faint)", fontSize: 11 }}>{it.count}</span>
          )}
        </a>
      ))}
    </nav>
  );
}
