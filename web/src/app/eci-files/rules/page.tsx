import type { Metadata } from "next";
import { Suspense } from "react";
import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
import { SectionHero } from "@/components/parliament/SectionHero";
import { EciRulesSkeleton } from "@/components/skeletons";
import { TextStatusBadge } from "@/components/eci-files/views/TextStatusBadge";
import { DrawerFromParam } from "@/components/eci-files/views/DrawerFromParam";
import { CrossLinks } from "@/components/eci-files/views/CrossLinks";
import { getEciRules } from "@/lib/api";
import { ECI_TEXT_STATUS_SHORT, eciEntryHref, formatEciDate } from "@/lib/eci-files";
import { StatusChip } from "@/components/eci-files/StatusChip";

export const metadata: Metadata = {
  title: "Rule changes · ECI Files",
  description: "Every rule, form and order change in the record, with the wording before and after where it could be sourced.",
  robots: { index: false, follow: false },
};

const BASE_PATH = "/eci-files/rules";

async function RulesBody({ entry }: { entry?: string }) {
  const page = await getEciRules().catch(() => null);
  if (!page) {
    return (
      <p style={{ color: "var(--muted)", padding: "24px 4px" }}>
        The record hasn&apos;t loaded — try again in a moment.
      </p>
    );
  }

  const groups: { year: string; rows: typeof page.rules }[] = [];
  for (const row of page.rules) {
    const year = row.entry.date ? row.entry.date.slice(0, 4) : "Undated";
    const last = groups[groups.length - 1];
    if (last && last.year === year) last.rows.push(row);
    else groups.push({ year, rows: [row] });
  }

  return (
    <>
      <div className="mono" style={{ fontSize: 12, color: "var(--muted)", margin: "-14px 0 26px" }}>
        {page.counts.rules} rule changes · {page.counts.diffs} before-and-after comparisons
      </div>

      {page.diffs.length > 0 && (
        <section style={{ marginBottom: 30 }}>
          <h2 className="mono" style={{ fontSize: 11, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--faint)", margin: "0 0 12px" }}>
            Before and after
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 12 }}>
            {page.diffs.map((d) => (
              <Link
                key={d.id}
                href={`${BASE_PATH}/${d.id}`}
                className="lift tap"
                style={{ display: "block", textDecoration: "none", color: "var(--ink)", border: "1px solid var(--rule)", borderRadius: 10, background: "var(--card2)", padding: "13px 15px" }}
              >
                <div className="serif" style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>{d.title}</div>
                <TextStatusBadge status={d.text_status} short />
              </Link>
            ))}
          </div>
        </section>
      )}

      {groups.map((g) => (
        <section key={g.year}>
          <h2 className="mono" style={{ fontSize: 13, color: "var(--muted)", margin: "18px 4px 8px" }}>{g.year}</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {g.rows.map((row) => (
              <div key={row.entry.id} style={{ border: "1px solid var(--rule)", borderRadius: 10, background: "var(--card2)", padding: "12px 15px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 4 }}>
                  <span className="mono" style={{ fontSize: 10.5, color: "var(--muted)" }}>{formatEciDate(row.entry.date, row.entry.date_precision)}</span>
                  <StatusChip status={row.entry.status} />
                </div>
                <Link href={eciEntryHref(row.entry.id, {}, BASE_PATH)} className="serif" style={{ display: "block", fontSize: 14.5, fontWeight: 600, color: "var(--ink)", textDecoration: "none", marginBottom: 4 }}>
                  {row.entry.title}
                </Link>
                <p style={{ fontSize: 13, color: "var(--ink2)", lineHeight: 1.5, margin: "0 0 6px" }}>{row.entry.summary}</p>
                {row.diffs.length > 0 && (
                  <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                    {row.diffs.map((d) => (
                      <Link key={d.id} href={`${BASE_PATH}/${d.id}`} className="mono" style={{ fontSize: 11.5, color: "var(--accent-2)", textDecoration: "none" }}>
                        Before and after → <span style={{ color: "var(--muted)" }}>({ECI_TEXT_STATUS_SHORT[d.text_status]})</span>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      ))}

      {entry && (
        <Suspense fallback={null}>
          <DrawerFromParam id={entry} basePath={BASE_PATH} />
        </Suspense>
      )}
    </>
  );
}

export default async function EciRulesPage({ searchParams }: { searchParams: Promise<{ entry?: string }> }) {
  const { entry } = await searchParams;
  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 1000, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
        <SectionHero
          eyebrow="ECI FILES · RULE CHANGES"
          title="Rule changes"
          subtitle="Every rule, form and order change in the record. Where the wording before and after could be sourced, it is set out line by line, with a label saying whether it comes from the document itself or from news reports."
          backHref="/eci-files"
          backLabel="ECI Files"
        />
        <Suspense fallback={<EciRulesSkeleton />}>
          <RulesBody entry={entry} />
        </Suspense>
        <CrossLinks current={BASE_PATH} />
      </main>
    </>
  );
}
