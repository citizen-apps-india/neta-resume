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
      {page.notes && (
        <p style={{ fontSize: 13, color: "var(--ink2)", lineHeight: 1.55, margin: "0 0 16px", maxWidth: "74ch" }}>
          <LinkifiedNote text={page.notes} basePath={BASE_PATH} />
        </p>
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
          subtitle="On 23 September 2026 The Indian Express reported that two of the three Election Commissioners, Sukhbir Singh Sandhu and Vivek Joshi, objected on record 14 times in ten months. This record can match 11 of those objections to a dated note or letter. The published reports do not itemise the other three."
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
