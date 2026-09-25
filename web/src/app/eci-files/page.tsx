import type { Metadata } from "next";
import { Suspense } from "react";
import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
import { SectionHero } from "@/components/parliament/SectionHero";
import { EciFrontSkeleton } from "@/components/skeletons";
import { HeroStats } from "@/components/eci-files/HeroStats";
import { QuestionCards } from "@/components/eci-files/QuestionCards";
import { KeyMomentsStrip } from "@/components/eci-files/KeyMomentsStrip";
import { getEciSummary, type EciSummary } from "@/lib/api";
import { formatLooseDate } from "@/lib/eci-files";

// Hidden until the owner approves: noindex/nofollow, unlinked, kept out of sitemap.ts. See
// docs/eci-files/SPEC.md — "Launch is gated."
export const metadata: Metadata = {
  title: "ECI Files",
  description: "A sourced, dated record of the Election Commission of India, 2019 to today.",
  robots: { index: false, follow: false },
};

/** The summary payload (headline stats, key moments, counts) and everything built from it. Its own async
 *  component so the static SectionHero paints immediately and this streams in beneath it — same pattern as
 *  the India Dashboard (`IndiaBody`). */
async function EciFrontBody() {
  let summary: EciSummary | null = null;
  try {
    summary = await getEciSummary();
  } catch {
    summary = null;
  }

  if (!summary) {
    return (
      <p style={{ color: "var(--muted)", padding: "24px 4px" }}>
        The record hasn&apos;t loaded — try again in a moment.
      </p>
    );
  }

  return (
    <>
      <HeroStats headline={summary.headline} />

      <div className="mono" style={{ fontSize: 11, color: "var(--muted)", margin: "-14px 0 26px" }}>
        {summary.counts.entries.toLocaleString("en-IN")} entries · {summary.counts.checked.toLocaleString("en-IN")} checked ·{" "}
        {summary.counts.people.toLocaleString("en-IN")} people named · {summary.counts.citations.toLocaleString("en-IN")} citations
        {summary.last_loaded && <> · updated {formatLooseDate(summary.last_loaded)}</>}
      </div>

      <QuestionCards />

      <KeyMomentsStrip moments={summary.key_moments} />

      <section style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 8 }}>
        <Link
          href="/eci-files/timeline"
          className="btnDark tap"
          style={{
            display: "inline-flex", alignItems: "center", gap: 8, textDecoration: "none",
            fontFamily: "var(--font-serif)", fontSize: 14, fontWeight: 600, padding: "12px 20px",
            borderRadius: 10, background: "var(--eci-ink)", color: "#fff",
          }}
        >
          Open the lane timeline →
        </Link>
        <Link
          href="/eci-files/entries"
          className="btnGhost tap"
          style={{
            display: "inline-flex", alignItems: "center", gap: 8, textDecoration: "none",
            fontFamily: "var(--font-serif)", fontSize: 14, fontWeight: 600, padding: "12px 20px",
            borderRadius: 10, border: "1px solid var(--border)", color: "var(--ink)",
          }}
        >
          Browse every entry
        </Link>
        <Link
          href="/eci-files/people"
          className="tap"
          style={{
            display: "inline-flex", alignItems: "center", fontSize: 13, color: "var(--accent-2)",
            textDecoration: "none", padding: "12px 8px",
          }}
        >
          People named in the record →
        </Link>
      </section>
    </>
  );
}

export default function EciFilesPage() {
  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 1000, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
        <SectionHero
          eyebrow="ECI FILES · SOURCED RECORD"
          title="What happened at the Election Commission, on the record"
          subtitle={
            <>
              A dated record of the Election Commission of India, 2019 to today — documents, reports and
              named claims, kept apart and each one linked to where it comes from. Every entry is labelled
              by how well it is sourced, and anything a fact-checker hasn&apos;t opened yet is marked
              &ldquo;not yet checked&rdquo; rather than presented as settled.
            </>
          }
        />
        <Suspense fallback={<EciFrontSkeleton />}>
          <EciFrontBody />
        </Suspense>
      </main>
    </>
  );
}
