import Link from "next/link";
import type { Metadata } from "next";
import { SiteHeader } from "@/components/SiteHeader";
import { AggregateLens } from "@/components/AggregateLens";
import { getThemeFocus, type ThemeFocusBreakdown } from "@/lib/api";

export const revalidate = 3600;
export const metadata: Metadata = {
  title: "By party · Parliament functioning · Neta·Resume",
  description: "What each party's MPs collectively raise in the 18th Lok Sabha, by policy theme — a descriptive comparison of focus.",
};

export default async function PartiesPage({ searchParams }: { searchParams: Promise<{ focus?: string }> }) {
  const { focus } = await searchParams;
  let data: ThemeFocusBreakdown | null = null;
  try {
    data = await getThemeFocus("party");
  } catch { /* API not up yet */ }

  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 900, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 64px", width: "100%" }}>
        <div style={{ marginBottom: 8 }}>
          <Link href="/parliament" className="mono" style={{ fontSize: 12, color: "var(--muted)", textDecoration: "none" }}>← Parliament functioning</Link>
        </div>
        <h1 className="serif" style={{ fontSize: "clamp(24px,5vw,32px)", fontWeight: 500, letterSpacing: "-0.02em", margin: "0 0 6px" }}>What parties raise</h1>
        <p style={{ fontSize: 15, color: "var(--ink2)", margin: "0 0 24px", maxWidth: "66ch" }}>
          Each {data?.house ?? "18th Lok Sabha"} party&rsquo;s questions, broken down by policy theme — the topics its
          members collectively emphasise. A descriptive comparison of focus, from the official record; never a ranking of merit.
        </p>

        {!data || data.groups.length === 0
          ? <p style={{ color: "var(--muted)" }}>Party data is loading…</p>
          : <AggregateLens groups={data.groups} kind="party" focus={focus} />}
      </main>
    </>
  );
}
