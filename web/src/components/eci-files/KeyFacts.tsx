import type { ReactNode } from "react";
import Link from "next/link";
import type { EciPersonGroup, EciSelection, EciSelectionRegime, EciStatusCounts, EciTenure } from "@/types/eci-files";
import {
  formatEciDate, formatTenureSpan, latestTenure, officeAbbrev, regimeForDate, regimeShortLabel, tenureDuration,
} from "@/lib/eci-files";
import { EntryCountLine } from "@/components/eci-files/StatusCountBar";

interface Tile { eyebrow: string; value: ReactNode; context?: ReactNode }

function latestAppointment(selections: EciSelection[], slug: string): EciSelection | null {
  return selections.find((s) => s.appointed.some((a) => a.person_slug === slug)) ?? null;
}

/** A row of at most 4 tiles — eyebrow, value, one line of context — dropping any tile with no value
 *  (PHASE4-SPEC.md §2.3). The commission group gets tenure-duration/selection/dissent tiles; secretariat
 *  and state get office/tenure/service. Every group gets "Entries on record". */
export function KeyFacts({
  slug, group, tenure, service, selections, regimes, statusCounts,
}: {
  slug: string;
  group: EciPersonGroup;
  tenure: EciTenure[];
  service: string | null;
  selections: EciSelection[];
  regimes: EciSelectionRegime[];
  statusCounts: EciStatusCounts;
}) {
  const tiles: Tile[] = [];

  if (group === "commission") {
    const dur = tenureDuration(tenure);
    if (dur.total !== "0 mo") {
      tiles.push({
        eyebrow: "Time at the Commission",
        value: dur.total,
        context: dur.byOffice.length > 0 ? dur.byOffice.map((o) => `${officeAbbrev(o.office)} ${o.label}`).join(" · ") : undefined,
      });
    }
    const sel = latestAppointment(selections, slug);
    if (sel) {
      tiles.push({
        eyebrow: "Selected under",
        value: <Link href="#selected-by" style={{ color: "var(--eci-ink)", textDecoration: "none" }}>{regimeShortLabel(sel.regime)}</Link>,
        context: formatEciDate(sel.date, sel.date_precision),
      });
      tiles.push({
        eyebrow: "Dissent at selection",
        value: sel.dissent.length > 0 ? `${sel.dissent.length} recorded` : "None recorded",
        context: sel.dissent.length > 0 ? sel.dissent.map((d) => d.name).join(", ") : undefined,
      });
    } else {
      const firstFrom = tenure.map((t) => t.from).filter((f): f is string => Boolean(f)).sort()[0] ?? null;
      const regime = regimeForDate(firstFrom, regimes);
      tiles.push({
        eyebrow: "Selected under",
        value: regime ? regimeShortLabel(regime.key) : "Executive convention",
        context: "appointed before 2019",
      });
    }
  } else {
    const t = latestTenure(tenure);
    if (t?.office) tiles.push({ eyebrow: "Office", value: t.office });
    tiles.push({ eyebrow: "In office", value: formatTenureSpan(t) });
    if (service) tiles.push({ eyebrow: "Service", value: <span style={{ fontSize: 14 }}>{service}</span> });
  }

  const total = statusCounts.documented + statusCounts.reported + statusCounts.claim + statusCounts.response;
  tiles.push({ eyebrow: "Entries on record", value: <EntryCountLine counts={statusCounts} total={total} /> });

  const shown = tiles.slice(0, 4);
  if (shown.length === 0) return null;

  return (
    <div className="eci-keyfacts" style={{ margin: "0 0 24px" }}>
      {shown.map((tile) => (
        <div key={tile.eyebrow} style={{ border: "1px solid var(--rule)", borderRadius: 10, background: "var(--card2)", padding: "12px 14px" }}>
          <div className="mono" style={{ fontSize: 9.5, letterSpacing: "0.06em", color: "var(--faint)", textTransform: "uppercase", marginBottom: 5 }}>
            {tile.eyebrow}
          </div>
          <div style={{ fontSize: 18, fontWeight: 600, color: "var(--ink)", lineHeight: 1.2 }}>{tile.value}</div>
          {tile.context && <div style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 4 }}>{tile.context}</div>}
        </div>
      ))}
    </div>
  );
}
