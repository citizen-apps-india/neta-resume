import Link from "next/link";
import type { Metadata } from "next";
import { SiteHeader } from "@/components/SiteHeader";
import { MinistryBars } from "@/components/MinistryBars";
import { HouseToggle } from "@/components/HouseToggle";
import { getParliamentMinistries, type House, type MinistryCount } from "@/lib/api";

export const revalidate = 3600;
export const metadata: Metadata = {
  title: "Ministries by questions · Parliament functioning · Neta·Resume",
  description: "Every Union ministry ranked by the number of parliamentary questions it fielded.",
};

export default async function MinistriesPage({ searchParams }: { searchParams: Promise<{ house?: string }> }) {
  const house: House = (await searchParams).house === "rs" ? "rs" : "ls";
  const hq = house === "rs" ? "?house=rs" : "";
  const houseLabel = house === "rs" ? "Rajya Sabha" : "18th Lok Sabha";
  let items: MinistryCount[] = [];
  try {
    items = await getParliamentMinistries(house);
  } catch { /* API not up yet */ }
  const total = items.reduce((n, m) => n + m.count, 0);

  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 820, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 64px", width: "100%" }}>
        <div style={{ marginBottom: 6 }}>
          <Link href={`/parliament${hq}`} className="mono" style={{ fontSize: 12, color: "var(--muted)", textDecoration: "none" }}>← Parliament functioning</Link>
        </div>
        <h1 className="serif" style={{ fontSize: "clamp(24px,5vw,32px)", fontWeight: 500, letterSpacing: "-0.02em", margin: "0 0 6px" }}>Ministries by questions</h1>
        <p style={{ fontSize: 15, color: "var(--ink2)", margin: "0 0 20px", maxWidth: "64ch" }}>
          Every Union ministry ranked by {houseLabel} questions ({total.toLocaleString("en-IN")} in all). Colours mark the policy theme; each links to the members who raise it.
        </p>
        <HouseToggle house={house} hrefLs="/parliament/ministries" hrefRs="/parliament/ministries?house=rs" />
        {items.length === 0 ? <p style={{ color: "var(--muted)" }}>No data.</p> : <MinistryBars items={items} />}
      </main>
    </>
  );
}
