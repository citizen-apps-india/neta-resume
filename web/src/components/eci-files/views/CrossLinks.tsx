import Link from "next/link";

const LINKS: { href: string; label: string }[] = [
  { href: "/eci-files/objections", label: "The fourteen objections" },
  { href: "/eci-files/answers", label: "Charge and answer" },
  { href: "/eci-files/rules", label: "Rule changes" },
  { href: "/eci-files/courts", label: "The court cases" },
];

/** The footer row every phase-5 page ends with (PHASE5-SPEC §6.1): a link to each of the other three new
 *  views, plus back to the ECI Files front page. */
export function CrossLinks({ current }: { current: string }) {
  const others = LINKS.filter((l) => l.href !== current);
  return (
    <nav style={{ marginTop: 40, paddingTop: 20, borderTop: "1px solid var(--rule)", display: "flex", flexWrap: "wrap", gap: "10px 22px" }}>
      <Link href="/eci-files" className="mono" style={{ fontSize: 12, color: "var(--muted)", textDecoration: "none" }}>← ECI Files</Link>
      {others.map((l) => (
        <Link key={l.href} href={l.href} className="mono" style={{ fontSize: 12, color: "var(--accent-2)", textDecoration: "none" }}>
          {l.label} →
        </Link>
      ))}
    </nav>
  );
}
