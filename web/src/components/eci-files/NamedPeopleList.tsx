import Link from "next/link";
import type { EciPersonSummary } from "@/types/eci-files";

/** The `named` group on `/eci-files/people` — judges, lawyers, ministers and party leaders with no
 *  profile of their own, just the entries that name them (PHASE4-SPEC.md §1.3). A CSS multi-column list,
 *  alphabetical, via `.eci-named-list` in globals.css. */
export function NamedPeopleList({ people }: { people: EciPersonSummary[] }) {
  const sorted = [...people].sort((a, b) => a.name.localeCompare(b.name));
  return (
    <ul className="eci-named-list" style={{ margin: 0, padding: 0, listStyle: "none" }}>
      {sorted.map((p) => (
        <li key={p.slug}>
          <Link href={`/eci-files/people/${p.slug}`} style={{ fontSize: 13, color: "var(--accent-2)", textDecoration: "none" }}>
            {p.name}
          </Link>{" "}
          <span className="mono" style={{ fontSize: 10.5, color: "var(--faint)" }}>{p.entry_count}</span>
        </li>
      ))}
    </ul>
  );
}
