import Link from "next/link";
import type { Metadata } from "next";
import { SiteHeader } from "@/components/SiteHeader";
import { AggregateLens } from "@/components/AggregateLens";
import { HouseToggle } from "@/components/HouseToggle";
import { getThemeFocus, type House, type ThemeFocusBreakdown } from "@/lib/api";

export const revalidate = 3600;
export const metadata: Metadata = {
  title: "By state · Parliament functioning · Neta·Resume",
  description: "What each state's MPs collectively raise in Parliament, by policy theme — a descriptive comparison of focus.",
};

export default async function StatesPage({ searchParams }: { searchParams: Promise<{ focus?: string; house?: string }> }) {
  const sp = await searchParams;
  const focus = sp.focus;
  const house: House = sp.house === "rs" ? "rs" : "ls";
  const hq = house === "rs" ? "?house=rs" : "";
  let data: ThemeFocusBreakdown | null = null;
  try {
    data = await getThemeFocus("state", house);
  } catch { /* API not up yet */ }

  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 900, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 64px", width: "100%" }}>
        <div style={{ marginBottom: 8 }}>
          <Link href={`/parliament${hq}`} className="mono" style={{ fontSize: 12, color: "var(--muted)", textDecoration: "none" }}>← Parliament functioning</Link>
        </div>
        <h1 className="serif" style={{ fontSize: "clamp(24px,5vw,32px)", fontWeight: 500, letterSpacing: "-0.02em", margin: "0 0 6px" }}>What states raise</h1>
        <p style={{ fontSize: 15, color: "var(--ink2)", margin: "0 0 20px", maxWidth: "66ch" }}>
          Each state&rsquo;s {data?.house ?? (house === "rs" ? "Rajya Sabha" : "18th Lok Sabha")} questions, broken down by policy theme — the topics its
          members collectively emphasise. A descriptive comparison of focus, from the official record; never a ranking of merit.
        </p>

        <HouseToggle house={house} hrefLs={`/parliament/states${focus ? `?focus=${encodeURIComponent(focus)}` : ""}`} hrefRs={`/parliament/states?house=rs${focus ? `&focus=${encodeURIComponent(focus)}` : ""}`} />

        {!data || data.groups.length === 0
          ? <p style={{ color: "var(--muted)" }}>State data is loading…</p>
          : <AggregateLens groups={data.groups} kind="state" focus={focus} />}
      </main>
    </>
  );
}
