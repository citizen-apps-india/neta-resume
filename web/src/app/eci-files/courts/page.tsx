import type { Metadata } from "next";
import { Suspense } from "react";
import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
import { SectionHero } from "@/components/parliament/SectionHero";
import { EciCourtsSkeleton } from "@/components/skeletons";
import { CaseCard } from "@/components/eci-files/views/CaseCard";
import { DrawerFromParam } from "@/components/eci-files/views/DrawerFromParam";
import { CrossLinks } from "@/components/eci-files/views/CrossLinks";
import { getEciCourts } from "@/lib/api";

export const metadata: Metadata = {
  title: "The court cases · ECI Files",
  description: "Five cases about the Commission's work, each with its parties, bench and status, and every recorded step in date order.",
  robots: { index: false, follow: false },
};

const BASE_PATH = "/eci-files/courts";

async function CourtsBody({ entry }: { entry?: string }) {
  const page = await getEciCourts().catch(() => null);
  if (!page) {
    return (
      <p style={{ color: "var(--muted)", padding: "24px 4px" }}>
        The record hasn&apos;t loaded — try again in a moment.
      </p>
    );
  }

  return (
    <>
      <div className="eci-courts-grid" style={{ marginBottom: 20 }}>
        {page.cases.map((c) => (
          <CaseCard key={c.slug} c={c} />
        ))}
      </div>

      {page.other_court_entries > 0 && (
        <p style={{ fontSize: 12.5, color: "var(--muted)" }}>
          {page.other_court_entries} other court entries are not grouped into a case.{" "}
          <Link href="/eci-files/timeline?lane=courts" className="mono" style={{ color: "var(--accent-2)", textDecoration: "none" }}>
            See them on the lane timeline →
          </Link>
        </p>
      )}

      {entry && (
        <Suspense fallback={null}>
          <DrawerFromParam id={entry} basePath={BASE_PATH} />
        </Suspense>
      )}
    </>
  );
}

export default async function EciCourtsPage({ searchParams }: { searchParams: Promise<{ entry?: string }> }) {
  const { entry } = await searchParams;
  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 1000, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
        <SectionHero
          eyebrow="ECI FILES · COURTS"
          title="The court cases"
          subtitle="Five cases about the Commission's work, each with its parties, bench and status, and every recorded step in date order."
          backHref="/eci-files"
          backLabel="ECI Files"
        />
        <Suspense fallback={<EciCourtsSkeleton />}>
          <CourtsBody entry={entry} />
        </Suspense>
        <CrossLinks current={BASE_PATH} />
      </main>
    </>
  );
}
