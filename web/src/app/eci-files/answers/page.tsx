import type { Metadata } from "next";
import { Suspense } from "react";
import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
import { SectionHero } from "@/components/parliament/SectionHero";
import { EciAnswersSkeleton } from "@/components/skeletons";
import { AnswerRow } from "@/components/eci-files/views/AnswerRow";
import { EntryRefLink } from "@/components/eci-files/views/EntryRefLink";
import { DrawerFromParam } from "@/components/eci-files/views/DrawerFromParam";
import { CrossLinks } from "@/components/eci-files/views/CrossLinks";
import { getEciAnswers } from "@/lib/api";
import type { EciAnswersView } from "@/types/eci-files";

export const metadata: Metadata = {
  title: "Charge and answer · ECI Files",
  description: "What was charged, what was the answer, and what does the record show.",
  robots: { index: false, follow: false },
};

const BASE_PATH = "/eci-files/answers";
type Params = { view?: string; entry?: string };

function isView(v?: string): v is EciAnswersView {
  return v === "all" || v === "no-response" || v === "with-record";
}

async function AnswersBody({ view, entry }: { view: EciAnswersView; entry?: string }) {
  const page = await getEciAnswers(view).catch(() => null);
  if (!page) {
    return (
      <p style={{ color: "var(--muted)", padding: "24px 4px" }}>
        The record hasn&apos;t loaded — try again in a moment.
      </p>
    );
  }

  const chips: { view: EciAnswersView; label: string; count: number }[] = [
    { view: "all", label: "All", count: page.counts.rows },
    { view: "no-response", label: "No response on record", count: page.counts.without_response },
    { view: "with-record", label: "With a document", count: page.counts.with_record },
  ];

  const groups: { year: string; rows: typeof page.rows }[] = [];
  for (const row of page.rows) {
    const year = row.charge.date ? row.charge.date.slice(0, 4) : "Undated";
    const last = groups[groups.length - 1];
    if (last && last.year === year) last.rows.push(row);
    else groups.push({ year, rows: [row] });
  }

  return (
    <>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 20 }}>
        {chips.map((c) => (
          <Link
            key={c.view}
            href={c.view === "all" ? BASE_PATH : `${BASE_PATH}?view=${c.view}`}
            aria-current={view === c.view ? "page" : undefined}
            className="tap"
            style={{
              fontSize: 12.5, padding: "6px 13px", borderRadius: 20, textDecoration: "none",
              border: `1px solid ${view === c.view ? "var(--accent)" : "var(--rule)"}`,
              background: view === c.view ? "var(--accent-soft)" : "var(--card2)",
              color: view === c.view ? "var(--accent-soft-fg)" : "var(--ink2)",
            }}
          >
            {c.label} {c.count}
          </Link>
        ))}
      </div>

      <div className="eci-answer-head">
        <div className="mono" style={{ fontSize: 10, letterSpacing: "0.05em", color: "var(--faint)" }}>WHAT WAS SAID OR DONE</div>
        <div className="mono" style={{ fontSize: 10, letterSpacing: "0.05em", color: "var(--faint)" }}>THE RESPONSE</div>
        <div className="mono" style={{ fontSize: 10, letterSpacing: "0.05em", color: "var(--faint)" }}>WHAT THE RECORD SHOWS</div>
      </div>

      {groups.map((g) => (
        <section key={g.year}>
          <h2 className="mono" style={{ fontSize: 13, color: "var(--muted)", margin: "18px 4px 4px" }}>{g.year}</h2>
          {g.rows.map((row) => (
            <AnswerRow key={row.charge.id} row={row} preserve={{ view: view === "all" ? undefined : view }} />
          ))}
        </section>
      ))}

      {page.unpaired_responses.length > 0 && (
        <section style={{ marginTop: 28 }}>
          <h2 className="serif" style={{ fontSize: 16, fontWeight: 600, margin: "0 0 10px" }}>Responses whose charge is not in the record</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {page.unpaired_responses.map((u) => (
              <div key={u.response.id} style={{ fontSize: 13 }}>
                <EntryRefLink entry={u.response} basePath={BASE_PATH} showStatus />
                {u.note && <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 2 }}>{u.note}</div>}
              </div>
            ))}
          </div>
        </section>
      )}

      {entry && (
        <Suspense fallback={null}>
          <DrawerFromParam id={entry} basePath={BASE_PATH} preserve={{ view: view === "all" ? undefined : view }} />
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
          subtitle="Each row sets what was said or done beside the response to it. A third column appears only where a primary document in the record bears directly on the point. Where no response is recorded, the row says so."
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
