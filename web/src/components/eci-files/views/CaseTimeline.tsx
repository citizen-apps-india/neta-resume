import Link from "next/link";
import type { EciCaseItem } from "@/types/eci-files";
import { eciEntryHref, formatEciDate } from "@/lib/eci-files";
import { StatusChip } from "@/components/eci-files/StatusChip";
import { RoleChip } from "@/components/eci-files/views/RoleChip";
import { PendingFlag } from "@/components/ui";

/** Every recorded step in one case, order by order — the model is a Supreme Court Observer case page
 *  (PHASE5-SPEC §6.5). A rail down the left, grouped by year; `related` items (linked but not part of the
 *  proceedings) sit at reduced emphasis with a hollow rail dot, and the last non-`related` item is
 *  labelled "Latest". */
interface YearGroup {
  year: string;
  items: EciCaseItem[];
}

/** Groups items by year (already date-ascending from the API), without mutating any binding the render
 *  callback below closes over — a plain pre-pass instead of a running "last year seen" variable. */
function groupByYear(items: EciCaseItem[]): YearGroup[] {
  const groups: YearGroup[] = [];
  for (const item of items) {
    const year = item.entry.date ? item.entry.date.slice(0, 4) : "—";
    const last = groups[groups.length - 1];
    if (last && last.year === year) last.items.push(item);
    else groups.push({ year, items: [item] });
  }
  return groups;
}

export function CaseTimeline({ slug, items }: { slug: string; items: EciCaseItem[] }) {
  const lastNonRelated = [...items].reverse().find((i) => i.role !== "related")?.entry.id;
  const basePath = `/eci-files/courts/${slug}`;
  const groups = groupByYear(items);

  return (
    <ol className="eci-case-timeline">
      {groups.flatMap((group, gi) => {
        const nodes: React.ReactNode[] = [
          <li key={`y-${group.year}`} className="eci-case-year mono" style={{ fontSize: 11.5, fontWeight: 700, color: "var(--muted)", marginTop: gi === 0 ? 0 : 6 }}>
            {group.year}
          </li>,
        ];
        for (const item of group.items) {
          const related = item.role === "related";
          nodes.push(
            <li key={item.entry.id} className={related ? "eci-related" : undefined} id={`item-${item.entry.id}`}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 3 }}>
                <span className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>{formatEciDate(item.entry.date, item.entry.date_precision)}</span>
                <RoleChip role={item.role} />
                <StatusChip status={item.entry.status} />
                {item.entry.check_status === "unchecked" && <PendingFlag>NOT YET CHECKED</PendingFlag>}
                {item.entry.id === lastNonRelated && (
                  <span className="mono" style={{ fontSize: 10, fontWeight: 700, color: "var(--eci-ink)", letterSpacing: "0.04em" }}>LATEST</span>
                )}
              </div>
              <h3 className="serif" style={{ fontSize: 14.5, fontWeight: 600, margin: "0 0 4px", color: related ? "var(--muted)" : "var(--ink)" }}>
                <Link href={eciEntryHref(item.entry.id, {}, basePath)} style={{ color: "inherit", textDecoration: "none" }}>{item.entry.title}</Link>
              </h3>
              <p
                style={{
                  fontSize: 13, lineHeight: 1.5, margin: 0, color: related ? "var(--muted)" : "var(--ink2)",
                  display: "-webkit-box", WebkitBoxOrient: "vertical", WebkitLineClamp: 2, overflow: "hidden",
                }}
              >
                {item.entry.summary}
              </p>
              {item.note && <p style={{ fontSize: 12, color: "var(--muted)", margin: "4px 0 0" }}>{item.note}</p>}
            </li>,
          );
        }
        return nodes;
      })}
    </ol>
  );
}
