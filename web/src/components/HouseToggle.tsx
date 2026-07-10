import Link from "next/link";
import type { House } from "@/lib/api";

/** LS/RS segmented toggle for the Parliament section. Server-rendered Links (like the search kind pills);
 *  each page passes hrefs that preserve its own params. Purely presentational — no client state. */
export function HouseToggle({ house, hrefLs, hrefRs }: { house: House; hrefLs: string; hrefRs: string }) {
  const base: React.CSSProperties = {
    fontSize: 12.5, fontWeight: 600, padding: "5px 14px", textDecoration: "none",
    border: "1px solid var(--border)",
  };
  const on: React.CSSProperties = { background: "var(--btn-bg)", color: "var(--btn-fg)", borderColor: "var(--btn-bg)" };
  const off: React.CSSProperties = { background: "var(--card2)", color: "var(--ink2)" };
  return (
    <div style={{ display: "inline-flex", borderRadius: 8, overflow: "hidden", marginBottom: 20 }} role="group" aria-label="House">
      <Link href={hrefLs} className="tap" style={{ ...base, ...(house === "ls" ? on : off), borderRadius: "8px 0 0 8px", borderRight: "none" }}>Lok Sabha</Link>
      <Link href={hrefRs} className="tap" style={{ ...base, ...(house === "rs" ? on : off), borderRadius: "0 8px 8px 0" }}>Rajya Sabha</Link>
    </div>
  );
}
