"use client";

import Link from "next/link";

/** Shown when a page cannot load its data (the API or database is down). The page still answers with
 *  an error status, so search engines retry later instead of dropping it. */
export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <main style={{ maxWidth: 560, margin: "0 auto", padding: "96px 24px", textAlign: "center" }}>
      <h1 style={{ fontSize: 28, marginBottom: 12, color: "var(--ink)" }}>This page is temporarily unavailable</h1>
      <p style={{ color: "var(--muted)", marginBottom: 28 }}>
        The record is still here; we could not reach it just now. Please try again in a few minutes.
      </p>
      <div style={{ display: "inline-flex", gap: 12 }}>
        <button type="button" className="btnDark" style={{ display: "inline-flex", fontFamily: "var(--font-serif)", fontSize: 14, fontWeight: 600, padding: "11px 22px", borderRadius: 9, border: "none", background: "var(--btn-bg)", color: "var(--btn-fg)", cursor: "pointer", textDecoration: "none" }} onClick={reset}>Try again</button>
        <Link href="/" className="btnGhost" style={{ display: "inline-flex", fontFamily: "var(--font-serif)", fontSize: 14, fontWeight: 600, padding: "11px 22px", borderRadius: 9, border: "1px solid var(--border)", background: "var(--card2)", color: "var(--ink)", cursor: "pointer", textDecoration: "none" }}>Home</Link>
      </div>
    </main>
  );
}
