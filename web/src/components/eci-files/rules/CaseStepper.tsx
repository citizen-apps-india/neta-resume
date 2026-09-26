import Link from "next/link";
import type { EciCaseItem } from "@/types/eci-files";
import { ECI_CASE_ROLE_LABEL, eciEntryHref, formatEciDate } from "@/lib/eci-files";

const STEP_WIDTH = 148;

/** The desktop view of `/eci-files/courts/[case]`: every recorded step as a metro-line stop, evenly
 *  spaced (a metro line spaces stops for legibility, not by the calendar days between them) so a case
 *  with hearings a week apart reads as clearly as one spread over a year. The outcome — the last
 *  non-`related` step — is the one stop drawn bigger, ringed and bold, so the result of the case never
 *  gets lost among its procedural steps. `CaseTimeline` renders the same items as a vertical rail for
 *  narrower screens; both are server-rendered and CSS alone picks which one shows. */
export function CaseStepper({ slug, items }: { slug: string; items: EciCaseItem[] }) {
  const basePath = `/eci-files/courts/${slug}`;
  const lastNonRelatedId = [...items].reverse().find((i) => i.role !== "related")?.entry.id;
  const n = Math.max(1, items.length - 1);

  return (
    <div className="eci-stepper">
      <div className="eci-stepper-scroll">
        <div className="eci-stepper-inner" style={{ minWidth: items.length * STEP_WIDTH }}>
          <span aria-hidden className="eci-stepper-line" />
          {items.map((item, i) => {
            const related = item.role === "related";
            const outcome = item.entry.id === lastNonRelatedId;
            const above = i % 2 === 0;
            const x = items.length === 1 ? 50 : (i / n) * 100;
            return (
              <Link
                key={item.entry.id}
                href={eciEntryHref(item.entry.id, {}, basePath)}
                className={`eci-stepper-stop${above ? " eci-stepper-stop--above" : ""}${outcome ? " eci-stepper-stop--outcome" : ""}${related ? " eci-stepper-stop--related" : ""}`}
                style={{ left: `${x}%` }}
              >
                <span aria-hidden className="eci-stepper-node" style={outcome ? undefined : { background: `var(--eci-lane-${item.entry.lane})` }} />
                <span className="eci-stepper-label">
                  <span className="eci-stepper-title">{item.entry.title}</span>
                  <span className="mono eci-stepper-date">{formatEciDate(item.entry.date, item.entry.date_precision)} · {ECI_CASE_ROLE_LABEL[item.role]}</span>
                </span>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
