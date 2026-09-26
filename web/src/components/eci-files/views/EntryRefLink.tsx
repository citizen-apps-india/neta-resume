import Link from "next/link";
import type { EciEntryRef } from "@/types/eci-files";
import { eciEntryHref, formatEciDate } from "@/lib/eci-files";
import { StatusChip } from "@/components/eci-files/StatusChip";
import { PendingFlag } from "@/components/ui";

/** One entry mention, used everywhere the new phase-5 views link to an entry: the date (precision-aware),
 *  the title, an optional small {@link StatusChip}, and a {@link PendingFlag} when the entry hasn't been
 *  checked. Opens the drawer on `basePath` via `?entry=`, preserving the page's other params. */
export function EntryRefLink({
  entry, basePath, preserve, showStatus = false,
}: {
  entry: EciEntryRef;
  basePath: string;
  preserve?: Record<string, string | undefined>;
  showStatus?: boolean;
}) {
  return (
    <Link
      href={eciEntryHref(entry.id, preserve, basePath)}
      style={{ display: "inline-flex", alignItems: "baseline", gap: 6, flexWrap: "wrap", color: "inherit", textDecoration: "none" }}
    >
      <span className="mono" style={{ fontSize: 10.5, color: "var(--muted)" }}>
        {formatEciDate(entry.date, entry.date_precision)}
      </span>
      <span style={{ fontSize: 13, color: "var(--accent-2)", textDecoration: "underline", textUnderlineOffset: 2 }}>
        {entry.title}
      </span>
      {showStatus && <StatusChip status={entry.status} />}
      {entry.check_status === "unchecked" && <PendingFlag>NOT YET CHECKED</PendingFlag>}
    </Link>
  );
}
