import type { Metadata } from "next";
import { Suspense } from "react";
import { SiteHeader } from "@/components/SiteHeader";
import { SectionHero } from "@/components/parliament/SectionHero";
import { EciObjectionsSkeleton } from "@/components/skeletons";
import { ObjectionsHero } from "@/components/eci-files/views2/ObjectionsHero";
import { ObjectionRows } from "@/components/eci-files/views2/ObjectionRows";
import { DrawerFromParam } from "@/components/eci-files/views/DrawerFromParam";
import { CrossLinks } from "@/components/eci-files/views/CrossLinks";
import { LinkifiedNote } from "@/components/eci-files/views/LinkifiedNote";
import { getEciObjections } from "@/lib/api";
import { eciEntryHref } from "@/lib/eci-files";

export const metadata: Metadata = {
  title: "The fourteen objections · ECI Files",
  description: "What the two Election Commissioners objected to on record, and what happened next.",
  robots: { index: false, follow: false },
};

const BASE_PATH = "/eci-files/objections";

async function ObjectionsBody({ entry }: { entry?: string }) {
  const page = await getEciObjections().catch(() => null);
  if (!page) {
    return (
      <p style={{ color: "var(--muted)", padding: "24px 4px" }}>
        The record hasn&apos;t loaded — try again in a moment.
      </p>
    );
  }

  const checkedAll = page.objections.every((o) => o.entries.every((e) => e.check_status === "checked"));

  return (
    <>
      {/* V1: the page had two paragraphs above the chart (this hero subtitle plus the notes below); the
          notes now collapse behind their own disclosure so a one-line lede is all that sits above it. */}
      {page.notes && (
        <details className="eci-more" style={{ margin: "0 0 16px" }}>
          <summary className="mono" style={{ fontSize: 11.5, color: "var(--accent-2)", cursor: "pointer" }}>About these objections</summary>
          <p style={{ fontSize: 13, color: "var(--ink2)", lineHeight: 1.55, margin: "8px 0 0", maxWidth: "74ch" }}>
            <LinkifiedNote text={page.notes} basePath={BASE_PATH} />
          </p>
        </details>
      )}

      <ObjectionsHero
        objections={page.objections}
        byPerson={page.by_person}
        missing={page.missing}
        reportedTotal={page.reported_total}
        response={page.response}
        basePath={BASE_PATH}
      />

      <ObjectionRows
        objections={page.objections}
        missing={page.missing}
        checkedAll={checkedAll}
        identified={page.identified}
        reportedTotal={page.reported_total}
        reportHref={page.report ? eciEntryHref(page.report.id, {}, BASE_PATH) : null}
      />

      {entry && (
        <Suspense fallback={null}>
          <DrawerFromParam id={entry} basePath={BASE_PATH} />
        </Suspense>
      )}
    </>
  );
}

export default async function EciObjectionsPage({ searchParams }: { searchParams: Promise<{ entry?: string }> }) {
  const { entry } = await searchParams;
  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 1080, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
        <SectionHero
          eyebrow="ECI FILES · THE FOURTEEN"
          title="The fourteen objections"
          subtitle="At least 14 objections by Sandhu and Joshi, November 2025 to September 2026."
          backHref="/eci-files"
          backLabel="ECI Files"
        />
        <Suspense fallback={<EciObjectionsSkeleton />}>
          <ObjectionsBody entry={entry} />
        </Suspense>
        <CrossLinks current={BASE_PATH} />
      </main>
    </>
  );
}
