import Link from "next/link";
import type { EciSelection } from "@/types/eci-files";
import { formatEciDate } from "@/lib/eci-files";

const PART_LABEL: Record<string, string> = {
  proposed: "Proposed", voted_with_majority: "Majority", recommended: "Recommended", dissented: "Dissented",
};

/** "Sat on selection panels" (PHASE4-SPEC.md §2.5.2) — for the small set of people who sat on a committee
 *  (Modi, Shah, Chowdhury, Gandhi, Meghwal) rather than being appointed: every selection where their part
 *  isn't `appointed`, one line each. */
export function PanelSeatsBlock({ slug, selections }: { slug: string; selections: EciSelection[] }) {
  const rows = selections
    .map((sel) => {
      const member = sel.members.find((m) => m.person_slug === slug);
      const isChair = sel.search?.chair_slug === slug;
      if (!member && !isChair) return null;
      return { sel, member, isChair };
    })
    .filter((r): r is { sel: EciSelection; member: EciSelection["members"][number] | undefined; isChair: boolean } => r !== null);

  if (rows.length === 0) return null;

  return (
    <section>
      <div className="mono" style={{ fontSize: 9.5, letterSpacing: "0.06em", color: "var(--faint)", marginBottom: 8 }}>SAT ON SELECTION PANELS</div>
      <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 8 }}>
        {rows.map(({ sel, member, isChair }) => (
          <li key={sel.id}>
            <Link href={`/eci-files/selections#${sel.id}`} style={{ textDecoration: "none", color: "var(--ink)" }}>
              <span className="mono" style={{ fontSize: 11.5, color: "var(--muted)", marginRight: 8 }}>{formatEciDate(sel.date, sel.date_precision)}</span>
              {isChair && !member ? (
                <span style={{ fontSize: 13.5 }}>Chaired the search committee</span>
              ) : (
                <>
                  <span style={{ fontSize: 13.5 }}>selected {sel.appointed.map((a) => a.name).join(", ")}</span>
                  {member && <span style={{ fontSize: 11.5, color: "var(--muted)", marginLeft: 8 }}>{member.role}</span>}
                  {member && (
                    <span className="eci-badge" data-part={member.part} style={{ marginLeft: 8 }}>
                      {PART_LABEL[member.part] ?? member.part}
                    </span>
                  )}
                </>
              )}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
