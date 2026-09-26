import type { Metadata } from "next";
import { Suspense } from "react";
import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
import { SectionHero } from "@/components/parliament/SectionHero";
import { EciObjectionsSkeleton } from "@/components/skeletons";
import { PersonAvatar } from "@/components/eci-files/views/PersonAvatar";
import { ObjectionStrip } from "@/components/eci-files/views/ObjectionStrip";
import { ObjectionLedger } from "@/components/eci-files/views/ObjectionLedger";
import { DrawerFromParam } from "@/components/eci-files/views/DrawerFromParam";
import { CrossLinks } from "@/components/eci-files/views/CrossLinks";
import { getEciObjections } from "@/lib/api";
import { eciEntryHref } from "@/lib/eci-files";
import { LinkifiedNote } from "@/components/eci-files/views/LinkifiedNote";

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

  return (
    <>
      {page.notes && (
        <p style={{ fontSize: 13, color: "var(--ink2)", lineHeight: 1.55, margin: "-8px 0 10px", maxWidth: "74ch" }}>
          <LinkifiedNote text={page.notes} basePath={BASE_PATH} />
        </p>
      )}
      {page.report && (
        <div style={{ margin: "0 0 14px" }}>
          <Link href={eciEntryHref(page.report.id, {}, BASE_PATH)} className="mono" style={{ fontSize: 12, color: "var(--accent-2)", textDecoration: "none" }}>
            Read the report →
          </Link>
        </div>
      )}

      <div className="mono" style={{ fontSize: 11, color: "var(--muted)", margin: "-14px 0 26px" }}>
        Numbered by date in this record, not by the newspaper.
      </div>

      {page.response && (
        <div style={{ borderLeft: "3px solid var(--eci-response)", background: "var(--card2)", borderRadius: "0 10px 10px 0", padding: "16px 18px", marginBottom: 26 }}>
          <h2 className="serif" style={{ fontSize: 15, fontWeight: 600, margin: "0 0 8px" }}>The Commission&apos;s response, 23 Sep 2026</h2>
          <p style={{ fontSize: 13.5, color: "var(--ink2)", lineHeight: 1.55, margin: "0 0 8px" }}>{page.response.summary}</p>
          {page.response.attributed_to && (
            <div style={{ fontSize: 12.5, color: "var(--muted)", marginBottom: 8 }}>
              Attributed to <strong style={{ color: "var(--ink2)", fontWeight: 500 }}>{page.response.attributed_to}</strong>
            </div>
          )}
          <Link href={eciEntryHref(page.response.id, {}, BASE_PATH)} className="mono" style={{ fontSize: 12, color: "var(--accent-2)", textDecoration: "none" }}>
            Read the press note →
          </Link>
        </div>
      )}

      <div style={{ display: "flex", flexWrap: "wrap", gap: 18, marginBottom: 22 }}>
        {page.by_person.map((p) => (
          <div key={p.slug} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <PersonAvatar name={p.name} photo={p.photo} size={32} decorative />
            <div>
              <Link href={`/eci-files/people/${p.slug}`} style={{ fontSize: 13.5, fontWeight: 600, color: "var(--ink)", textDecoration: "none" }}>{p.name}</Link>
              <div className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>
                {p.count} objections{p.joint > 0 ? ` · ${p.joint} jointly` : ""}
              </div>
            </div>
          </div>
        ))}
      </div>

      <ObjectionStrip objections={page.objections} byPerson={page.by_person} />

      <ObjectionLedger objections={page.objections} missing={page.missing} />

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
      <main style={{ maxWidth: 900, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
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
