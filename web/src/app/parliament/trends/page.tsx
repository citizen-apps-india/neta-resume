import Link from "next/link";
import type { Metadata } from "next";
import { SiteHeader } from "@/components/SiteHeader";
import { ThemeStackedArea } from "@/components/resume/charts";
import { getParliamentTrends, type Trends } from "@/lib/api";

export const revalidate = 3600;
export const metadata: Metadata = {
  title: "Trends over time · Parliament functioning · Neta·Resume",
  description: "How the 18th Lok Sabha's attention shifted month to month across the seven policy themes.",
};

const cardStyle: React.CSSProperties = { border: "1px solid var(--rule)", borderRadius: 12, background: "var(--card2)", padding: "clamp(16px,3vw,24px)" };

export default async function TrendsPage() {
  let t: Trends | null = null;
  try {
    t = await getParliamentTrends();
  } catch { /* API not up yet */ }

  const total = t?.totals.reduce((n, v) => n + v, 0) ?? 0;

  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 1120, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 64px", width: "100%" }}>
        <div style={{ marginBottom: 8 }}>
          <Link href="/parliament" className="mono" style={{ fontSize: 12, color: "var(--muted)", textDecoration: "none" }}>← Parliament functioning</Link>
        </div>
        <h1 className="serif" style={{ fontSize: "clamp(24px,5vw,32px)", fontWeight: 500, letterSpacing: "-0.02em", margin: "0 0 6px" }}>Trends over time</h1>
        <p style={{ fontSize: 15, color: "var(--ink2)", margin: "0 0 24px", maxWidth: "66ch" }}>
          {t?.house ?? "18th Lok Sabha"} questions by month, stacked by policy theme — how the House&rsquo;s attention shifted across the term
          {total ? <> ({total.toLocaleString("en-IN")} questions in all)</> : null}.
        </p>

        {!t || t.months.length === 0 ? (
          <p style={{ color: "var(--muted)" }}>Trends data is loading…</p>
        ) : (
          <>
            <div style={cardStyle}>
              <ThemeStackedArea months={t.months} series={t.series} />
            </div>
            <p style={{ fontSize: 12.5, color: "var(--muted)", margin: "16px 0 0", maxWidth: "72ch" }}>
              Volume tracks the parliamentary calendar — peaks fall in the Budget (Feb–Mar) and Winter (Dec) sessions,
              with near-zero months when the House isn&rsquo;t sitting. Themes come from the ministry each question
              addressed. Missing ≠ zero: a quiet month is a recess, not disengagement.
            </p>
          </>
        )}
      </main>
    </>
  );
}
