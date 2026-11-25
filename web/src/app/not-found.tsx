import type { Metadata } from "next";
import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";

export const metadata: Metadata = { title: "Not found", robots: { index: false, follow: true } };

export default function NotFound() {
  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 560, margin: "0 auto", padding: "96px 24px", textAlign: "center" }}>
        <h1 style={{ fontSize: 28, marginBottom: 12, color: "var(--ink)" }}>We could not find that page</h1>
        <p style={{ color: "var(--muted)", marginBottom: 28 }}>
          It may have moved, or the legislator is not in the record yet.
        </p>
        <Link href="/directory" className="btnDark" style={{ display: "inline-flex", fontFamily: "var(--font-serif)", fontSize: 14, fontWeight: 600, padding: "11px 22px", borderRadius: 9, border: "none", background: "var(--btn-bg)", color: "var(--btn-fg)", cursor: "pointer", textDecoration: "none" }}>Browse every legislator</Link>
      </main>
    </>
  );
}
