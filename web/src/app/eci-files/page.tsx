import type { Metadata } from "next";
import { SiteHeader } from "@/components/SiteHeader";
import { SectionHero } from "@/components/parliament/SectionHero";
import { Filters } from "@/components/eci-files/Filters";
import { Timeline } from "@/components/eci-files/Timeline";
import { getEciTimeline, type EciTimeline } from "@/lib/api";

// Hidden until the owner approves: noindex/nofollow, unlinked, kept out of sitemap.ts. See
// docs/eci-files/SPEC.md — "Launch is gated."
export const metadata: Metadata = {
  title: "ECI Files · Neta·Resume",
  description: "A sourced, dated record of the Election Commission of India, 2019 to today.",
  robots: { index: false, follow: false },
};

export default async function EciFilesPage({
  searchParams,
}: {
  searchParams: Promise<{ topic?: string; person?: string }>;
}) {
  const sp = await searchParams;
  const topic = sp.topic || undefined;
  const person = sp.person || undefined;

  let timeline: EciTimeline | null = null;
  try {
    timeline = await getEciTimeline({ topic, person });
  } catch {
    timeline = null;
  }

  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 900, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
        <SectionHero
          eyebrow="ECI FILES · SOURCED RECORD"
          title="ECI Files"
          subtitle={
            <>
              A dated record of the Election Commission of India, 2019 to today — documents, reports and
              named claims, kept apart and each one linked to where it comes from. Every entry is labelled by
              how well it is sourced, and anything a fact-checker hasn&apos;t opened yet is marked
              &ldquo;not yet checked&rdquo; rather than presented as settled.
            </>
          }
        />

        {timeline === null ? (
          <p style={{ color: "var(--muted)", padding: "24px 4px" }}>
            The record hasn&apos;t loaded — try again in a moment.
          </p>
        ) : (
          <>
            <Filters
              basePath="/eci-files"
              topics={timeline.topics}
              people={timeline.people}
              topic={topic}
              person={person}
            />
            <div className="mono" style={{ fontSize: 11.5, color: "var(--muted)", marginBottom: 16 }}>
              {timeline.entries.length} entr{timeline.entries.length === 1 ? "y" : "ies"}
              {" · "}
              {timeline.counts.unchecked} not yet checked
            </div>
            <Timeline entries={timeline.entries} />
          </>
        )}
      </main>
    </>
  );
}
