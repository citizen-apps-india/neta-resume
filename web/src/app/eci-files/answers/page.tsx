import type { Metadata } from "next";
import { Suspense } from "react";
import { SiteHeader } from "@/components/SiteHeader";
import { SectionHero } from "@/components/parliament/SectionHero";
import { EciAnswersSkeleton } from "@/components/skeletons";
import { AnswersHero } from "@/components/eci-files/views2/AnswersHero";
import { AnswerFilterChips } from "@/components/eci-files/views2/AnswerFilterChips";
import { ChargeAnswerRow } from "@/components/eci-files/views2/ChargeAnswerRow";
import { EntryRow } from "@/components/eci-files/ui/EntryRow";
import { DrawerFromParam } from "@/components/eci-files/views/DrawerFromParam";
import { CrossLinks } from "@/components/eci-files/views/CrossLinks";
import { getEciAnswers } from "@/lib/api";
import { eciEntryHref, filterEciAnswerRows, formatEciDate, type EciAnswersView2 } from "@/lib/eci-files";

export const metadata: Metadata = {
  title: "Charge and answer · ECI Files",
  description: "What was charged, what was the answer, and what does the record show.",
  robots: { index: false, follow: false },
};

const BASE_PATH = "/eci-files/answers";
type Params = { view?: string; entry?: string };

function isView(v?: string): v is EciAnswersView2 {
  return v === "all" || v === "no-response" || v === "with-record" || v === "with-response";
}

async function AnswersBody({ view, entry }: { view: EciAnswersView2; entry?: string }) {
  const page = await getEciAnswers("all").catch(() => null);
  if (!page) {
    return (
      <p style={{ color: "var(--muted)", padding: "24px 4px" }}>
        The record hasn&apos;t loaded — try again in a moment.
      </p>
    );
  }

  const rows = filterEciAnswerRows(page.rows, view);
  const preserve = { view: view === "all" ? undefined : view };

  const groups: { year: string; rows: typeof rows }[] = [];
  for (const row of rows) {
    const year = row.charge.date ? row.charge.date.slice(0, 4) : "Undated";
    const last = groups[groups.length - 1];
    if (last && last.year === year) last.rows.push(row);
    else groups.push({ year, rows: [row] });
  }

  return (
    <>
      <AnswersHero rows={page.rows} counts={page.counts} />
      <AnswerFilterChips view={view} counts={page.counts} />

      <div className="eci2-answer-head">
        <span className="mono eci2-eyebrow">What was said or done</span>
        <span className="mono eci2-eyebrow">The reply</span>
      </div>

      {groups.map((g) => (
        <section key={g.year}>
          <h2 className="mono" style={{ fontSize: 13, color: "var(--muted)", margin: "18px 4px 4px" }}>{g.year} · {g.rows.length} charges</h2>
          {g.rows.map((row) => (
            <ChargeAnswerRow key={row.charge.id} row={row} preserve={preserve} />
          ))}
        </section>
      ))}

      {page.unpaired_responses.length > 0 && view === "all" && (
        <section style={{ marginTop: 28 }}>
          <h2 className="serif" style={{ fontSize: 16, fontWeight: 600, margin: "0 0 10px" }}>Responses whose charge is not in the record</h2>
          <div>
            {page.unpaired_responses.map((u) => (
              <EntryRow
                key={u.response.id}
                date={formatEciDate(u.response.date, u.response.date_precision)}
                lane={u.response.lane}
                title={u.response.title}
                href={eciEntryHref(u.response.id, preserve, BASE_PATH)}
                status={u.response.status}
                checked={u.response.check_status === "checked"}
                extra={u.note ? <span style={{ fontSize: 12, color: "var(--muted)" }}>{u.note}</span> : undefined}
              />
            ))}
          </div>
        </section>
      )}

      {entry && (
        <Suspense fallback={null}>
          <DrawerFromParam id={entry} basePath={BASE_PATH} preserve={preserve} />
        </Suspense>
      )}
    </>
  );
}

export default async function EciAnswersPage({ searchParams }: { searchParams: Promise<Params> }) {
  const sp = await searchParams;
  const view = isView(sp.view) ? sp.view : "all";
  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 1120, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
        <SectionHero
          eyebrow="ECI FILES · CHARGE AND ANSWER"
          title="Charge and answer"
          subtitle="Every charge set beside its reply, at equal weight, with what the record shows."
          backHref="/eci-files"
          backLabel="ECI Files"
        />
        <Suspense fallback={<EciAnswersSkeleton />}>
          <AnswersBody view={view} entry={sp.entry} />
        </Suspense>
        <CrossLinks current={BASE_PATH} />
      </main>
    </>
  );
}
