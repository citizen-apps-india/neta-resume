import type { EciCasePage } from "@/types/eci-files";
import { formatEciDate } from "@/lib/eci-files";

function Fact({ term, value }: { term: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="mono" style={{ fontSize: 10, letterSpacing: "0.06em", color: "var(--faint)" }}>{term.toUpperCase()}</dt>
      <dd style={{ margin: "2px 0 0", fontSize: 13, color: "var(--ink)" }}>{value ?? "—"}</dd>
    </div>
  );
}

function NameList({ names }: { names: string[] }) {
  if (names.length === 0) return <>—</>;
  return <>{names.join(", ")}</>;
}

/** The facts panel on `/eci-files/courts/[case]` — court, case number, bench, citation, parties and when
 *  the case was first recorded. A `<dl>` per PHASE5-SPEC §6.5; missing values render "—". */
export function CaseFacts({ page }: { page: EciCasePage }) {
  return (
    <dl className="eci-case-facts">
      <Fact term="Court" value={page.court} />
      <Fact term="Case number" value={page.case_number ? <span className="mono">{page.case_number}</span> : null} />
      <Fact term="Bench" value={page.bench} />
      {page.citation && <Fact term="Citation" value={<span className="mono">{page.citation}</span>} />}
      <Fact term="Petitioners" value={<NameList names={page.parties.petitioners} />} />
      <Fact term="Respondents" value={<NameList names={page.parties.respondents} />} />
      <Fact term="Filed or first recorded" value={formatEciDate(page.case.date, page.case.date_precision)} />
    </dl>
  );
}
