import Link from "next/link";
import type { EciPersonSummary } from "@/types/eci-files";
import { formatStatusCounts, formatTenureSpan, latestTenure } from "@/lib/eci-files";

/** The `state` group on `/eci-files/people` (PHASE4-SPEC.md §1.3): one row per State Chief Electoral
 *  Officer, as a real `<table>` (not divs) so the caption and headers stay in the accessibility tree. Rows
 *  collapse to two lines each under 640px via `.eci-state-table` in globals.css. */
export function StateOfficerTable({ people }: { people: EciPersonSummary[] }) {
  return (
    <table className="eci-state-table">
      <caption style={{ textAlign: "left", fontSize: 12.5, color: "var(--muted)", padding: "0 0 10px" }}>
        State Chief Electoral Officers named in the record.
      </caption>
      <thead>
        <tr>
          <th scope="col">State</th>
          <th scope="col">Name</th>
          <th scope="col">In office</th>
          <th scope="col">Entries</th>
        </tr>
      </thead>
      <tbody>
        {people.map((p) => {
          const state = (p.role ?? "").replace(/^Chief Electoral Officer,\s*/, "") || "—";
          const total = p.status_counts.documented + p.status_counts.reported + p.status_counts.claim + p.status_counts.response;
          return (
            <tr key={p.slug}>
              <td className="mono" style={{ fontSize: 11.5, color: "var(--muted)" }}>{state}</td>
              <td>
                <Link href={`/eci-files/people/${p.slug}`} style={{ color: "var(--ink)", fontWeight: 600, textDecoration: "none" }}>
                  {p.name}
                </Link>
              </td>
              <td className="mono" style={{ fontSize: 12, color: "var(--ink2)" }}>{formatTenureSpan(latestTenure(p.tenure))}</td>
              <td className="mono" style={{ fontSize: 11, color: "var(--faint)" }}>{formatStatusCounts(total, p.status_counts)}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
