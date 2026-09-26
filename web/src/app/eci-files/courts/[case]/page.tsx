import type { Metadata } from "next";
import { Suspense } from "react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { SiteHeader } from "@/components/SiteHeader";
import { EciCaseSkeleton } from "@/components/skeletons";
import { CaseFacts } from "@/components/eci-files/views/CaseFacts";
import { CaseTimeline } from "@/components/eci-files/views/CaseTimeline";
import { CaseStepper } from "@/components/eci-files/rules/CaseStepper";
import { CitationList } from "@/components/eci-files/CitationList";
import { DrawerFromParam } from "@/components/eci-files/views/DrawerFromParam";
import { CrossLinks } from "@/components/eci-files/views/CrossLinks";
import { getEciCase } from "@/lib/api";
import { ECI_CASE_STATUS_LABEL, ECI_LOAD_FAILED_MESSAGE, eciEntryHref, formatEciDate, loadEciItem } from "@/lib/eci-files";
import type { EciCaseShortStatus } from "@/types/eci-files";

const STATUS_PROSE: Record<EciCaseShortStatus, string> = {
  disposed: "decided, not pending",
  pending: "still pending",
  referred: "referred to the Chief Justice",
};

type Params = { case: string };

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const { case: slug } = await params;
  const page = await getEciCase(slug).catch(() => null);
  return {
    title: page ? `${page.case_name} · Courts · ECI Files` : "Case not found · ECI Files",
    description: page ? `${page.short_name}: every recorded step, order by order.` : undefined,
    };
}

async function CaseBody({ slug, entry }: { slug: string; entry?: string }) {
  const result = await loadEciItem(() => getEciCase(slug));
  if (result.status === "not_found") notFound();
  if (result.status === "error") {
    return <p style={{ color: "var(--muted)", padding: "24px 4px" }}>{ECI_LOAD_FAILED_MESSAGE}</p>;
  }
  const page = result.data;
  const basePath = `/eci-files/courts/${slug}`;

  // "Related" items (an earlier judgment, a later separate petition) are context, not steps in this case.
  const steps = page.items.filter((i) => i.role !== "related");
  return (
    <>
      <div style={{ marginBottom: 14 }}>
        <Link href="/eci-files/courts" className="mono" style={{ fontSize: 12, color: "var(--muted)", textDecoration: "none" }}>← Courts</Link>
      </div>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 12, flexWrap: "wrap", marginBottom: 20 }}>
        <h1 className="serif" style={{ fontSize: "clamp(24px,4.6vw,32px)", fontWeight: 500, letterSpacing: "-0.02em", margin: 0, flex: "1 1 auto", minWidth: 0 }}>
          {page.case_name}
        </h1>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
          <span className="mono" style={{ fontSize: 10.5, fontWeight: 600, padding: "4px 10px", borderRadius: 999, border: "1px solid var(--border2)", color: "var(--ink2)", background: "var(--sunken)" }}>
            {ECI_CASE_STATUS_LABEL[page.short_status]}
          </span>
          {page.status_note && <span style={{ fontSize: 12.5, color: "var(--muted)" }}>{page.status_note}</span>}
        </div>
      </div>
      {steps.length > 0 && (
        <p style={{ fontSize: 14, color: "var(--ink2)", margin: "-14px 0 20px" }}>
          {steps.length} recorded step{steps.length === 1 ? "" : "s"}, {formatEciDate(steps[0].entry.date, steps[0].entry.date_precision)}{" "}
          to {formatEciDate(steps[steps.length - 1].entry.date, steps[steps.length - 1].entry.date_precision)} — {STATUS_PROSE[page.short_status]}.
        </p>
      )}

      <section style={{ marginBottom: 26 }}>
        <h2 className="serif" style={{ fontSize: 17, fontWeight: 600, margin: "0 0 14px" }}>Every recorded step</h2>
        <div className="eci-case-desktop-only">
          <CaseStepper slug={slug} items={page.items} />
        </div>
        <div className="eci-case-mobile-only">
          <CaseTimeline slug={slug} items={page.items} />
        </div>
      </section>

      <CaseFacts page={page} />

      <section style={{ margin: "26px 0" }}>
        <h2 className="serif" style={{ fontSize: 17, fontWeight: 600, margin: "0 0 8px" }}>In brief</h2>
        <p style={{ fontSize: 13.5, color: "var(--ink2)", lineHeight: 1.6, margin: "0 0 4px", maxWidth: "72ch", display: "-webkit-box", WebkitBoxOrient: "vertical", WebkitLineClamp: 2, overflow: "hidden" }}>
          {page.case.summary}
        </p>
        <details className="eci-more" style={{ marginBottom: 12 }}>
          <summary className="mono" style={{ fontSize: 12.5, color: "var(--accent-2)", fontWeight: 600, cursor: "pointer" }}>Read more</summary>
          <p style={{ fontSize: 13.5, color: "var(--ink2)", lineHeight: 1.6, margin: "8px 0 0", maxWidth: "72ch" }}>{page.case.summary}</p>
        </details>
        <div className="mono" style={{ fontSize: 9.5, letterSpacing: "0.06em", color: "var(--faint)", marginBottom: 6 }}>SOURCES</div>
        <CitationList citations={page.case.citations} />
        <Link href={eciEntryHref(page.case.id, {}, basePath)} className="mono" style={{ display: "inline-block", marginTop: 10, fontSize: 12, color: "var(--accent-2)", textDecoration: "none" }}>
          Open the full entry →
        </Link>
      </section>

      {entry && (
        <Suspense fallback={null}>
          <DrawerFromParam id={entry} basePath={basePath} />
        </Suspense>
      )}
    </>
  );
}

export default async function EciCasePage({ params, searchParams }: { params: Promise<Params>; searchParams: Promise<{ entry?: string }> }) {
  const { case: slug } = await params;
  const { entry } = await searchParams;
  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 900, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
        <Suspense fallback={<EciCaseSkeleton />}>
          <CaseBody slug={slug} entry={entry} />
        </Suspense>
        <CrossLinks current="/eci-files/courts" />
      </main>
    </>
  );
}
