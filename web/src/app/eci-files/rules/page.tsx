import type { Metadata } from "next";
import { Suspense } from "react";
import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
import { SectionHero } from "@/components/parliament/SectionHero";
import { EciRulesSkeleton } from "@/components/skeletons";
import { DrawerFromParam } from "@/components/eci-files/views/DrawerFromParam";
import { CrossLinks } from "@/components/eci-files/views/CrossLinks";
import { RulesTimeAxis } from "@/components/eci-files/rules/RulesTimeAxis";
import { RuleComparisonCard } from "@/components/eci-files/rules/RuleComparisonCard";
import { getEciRuleDiff, getEciRules } from "@/lib/api";
import { ECI_TEXT_STATUS_SHORT, eciEntryHref, formatEciDate } from "@/lib/eci-files";
import { StatusChip } from "@/components/eci-files/StatusChip";
import type { EciRuleDiff } from "@/types/eci-files";

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

  const comparisons = (await Promise.all(page.diffs.map((d) => getEciRuleDiff(d.id).catch(() => null))))
    .filter((d): d is EciRuleDiff => d !== null);

  const years = page.rules.map((r) => r.entry.date?.slice(0, 4)).filter((y): y is string => !!y);
  const yearRange = years.length > 0 ? `${years[years.length - 1]}–${years[0]}` : null;

  const groups: { year: string; rows: typeof page.rules }[] = [];
  for (const row of page.rules) {
    const year = row.entry.date ? row.entry.date.slice(0, 4) : "Undated";
    const last = groups[groups.length - 1];
    if (last && last.year === year) last.rows.push(row);
    else groups.push({ year, rows: [row] });
  }

  return (
    <>
      {/* the one visual answer: every rule change on a single time axis, above the fold */}
      <div style={{ display: "flex", flexDirection: "column", gap: 14, background: "var(--card)", border: "1px solid var(--rule)", borderRadius: 14, padding: "20px 22px", marginBottom: 30 }}>
        <div className="mono" style={{ fontSize: 11.5, color: "var(--muted)" }}>
          {page.counts.rules} rule changes · {page.counts.diffs} with a before-and-after{yearRange ? ` · ${yearRange}` : ""}
        </div>
        <RulesTimeAxis rows={page.rules} />
      </div>

      {comparisons.length > 0 && (
        <section style={{ marginBottom: 30 }}>
          <h2 className="mono" style={{ fontSize: 11, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--faint)", margin: "0 0 12px" }}>
            Before and after
          </h2>
          <div className="eci-rule-cards">
            {comparisons.map((d) => <RuleComparisonCard key={d.id} diff={d} />)}
          </div>
        </section>
      )}

      {groups.map((g) => (
        <section key={g.year}>
          <h2 className="mono" style={{ fontSize: 13, color: "var(--muted)", margin: "18px 4px 8px" }}>{g.year}</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {g.rows.map((row) => (
              <div
                key={row.entry.id}
                id={`rule-${row.entry.id}`}
                className={row.diffs.length > 0 ? "eci-rule-row--diffed" : undefined}
                style={{ border: "1px solid var(--rule)", borderRadius: 10, background: "var(--card2)", padding: "12px 15px", scrollMarginTop: 72 }}
              >
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
          subtitle="Every rule, form and order change in the record, sourced line by line."
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
