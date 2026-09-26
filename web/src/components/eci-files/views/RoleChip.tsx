import type { EciCaseRole } from "@/types/eci-files";
import { ECI_CASE_ROLE_LABEL } from "@/lib/eci-files";

/** A court-case step's role — text, never colour, per house rule (PHASE5-SPEC §5/§7). `related` and
 *  `compliance` read at reduced emphasis; every other role reads the same as the entry's own status. */
export function RoleChip({ role }: { role: EciCaseRole }) {
  const muted = role === "related";
  return (
    <span
      className="eci-role-chip mono"
      style={muted ? { opacity: 0.75 } : undefined}
    >
      {ECI_CASE_ROLE_LABEL[role]}
    </span>
  );
}
