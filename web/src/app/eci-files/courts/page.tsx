import type { Metadata } from "next";
import { Suspense } from "react";
import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
import { SectionHero } from "@/components/parliament/SectionHero";
import { EciCourtsSkeleton } from "@/components/skeletons";
import { DrawerFromParam } from "@/components/eci-files/views/DrawerFromParam";
import { CrossLinks } from "@/components/eci-files/views/CrossLinks";
import { CourtsTracks } from "@/components/eci-files/rules/CourtsTracks";
import { getEciCourts } from "@/lib/api";
import { ECI_CASE_STATUS_LABEL, formatEciDate } from "@/lib/eci-files";

export const metadata: Metadata = {
  title: "The court cases · ECI Files",
  description: "Five cases touching the Commission, filed to judgment or pending, on one clock.",
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
      <div style={{ display: "flex", flexDirection: "column", gap: 14, background: "var(--card)", border: "1px solid var(--rule)", borderRadius: 14, padding: "20px 22px", marginBottom: 26 }}>
        <div className="mono" style={{ fontSize: 11.5, color: "var(--muted)" }}>
          {page.cases.length} case{page.cases.length === 1 ? "" : "s"} · filed → orders → judgment or pending
        </div>
        <CourtsTracks cases={page.cases} />
      </div>

      <section style={{ marginBottom: 20 }}>
        <h2 className="mono" style={{ fontSize: 11, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--faint)", margin: "0 0 12px" }}>
          Latest in each case
        </h2>
        <div className="eci-latest-list">
          {page.cases.map((c) => (
            <Link key={c.slug} href={`${BASE_PATH}/${c.slug}`} className="eci-latest-row lift tap">
              <div style={{ display: "flex", flexDirection: "column", gap: 2, minWidth: 0 }}>
                <b className="serif" style={{ fontSize: 14.5 }}>{c.short_name}</b>
                {c.case_number && <span className="mono" style={{ fontSize: 11, color: "var(--muted)", overflowWrap: "anywhere" }}>{c.case_number}</span>}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 2, minWidth: 0 }}>
                {c.latest ? (
                  <>
                    <span style={{ fontSize: 13, color: "var(--ink2)" }}>{c.latest.title}</span>
                    <span className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>{formatEciDate(c.latest.date, c.latest.date_precision)}</span>
                  </>
                ) : (
                  <span style={{ fontSize: 13, color: "var(--muted)" }}>Nothing recorded yet</span>
                )}
              </div>
              <span
                className="mono"
                style={{
                  justifySelf: "end", fontSize: 11, fontWeight: 650, padding: "3px 9px", borderRadius: 999,
                  border: "1px solid var(--border2)", background: "var(--sunken)", color: "var(--ink2)", whiteSpace: "nowrap",
                }}
              >
                {ECI_CASE_STATUS_LABEL[c.short_status]}
              </span>
            </Link>
          ))}
        </div>
      </section>

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
          subtitle="Five cases touching the Commission, filed to judgment or pending, on one clock."
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
