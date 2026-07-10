import Link from "next/link";
import type { House } from "@/lib/api";

/** LS/RS segmented control for the Parliament section — a pill-in-track (active pill raised on a sunken
 *  track). Server-rendered Links (like the search kind pills); each page passes hrefs that preserve its own
 *  params. Purely presentational. Same props/API as before. */
export function HouseToggle({ house, hrefLs, hrefRs }: { house: House; hrefLs: string; hrefRs: string }) {
  const pill = (active: boolean): React.CSSProperties => ({
    fontSize: 12.5, fontWeight: 600, padding: "6px 15px", borderRadius: 8, textDecoration: "none",
    background: active ? "var(--card2)" : "transparent",
    color: active ? "var(--ink)" : "var(--muted)",
    border: `1px solid ${active ? "var(--border)" : "transparent"}`,
    boxShadow: active ? "0 1px 3px -1px var(--shadow)" : "none",
  });
  return (
    <div role="group" aria-label="House" style={{ display: "inline-flex", gap: 3, padding: 3, borderRadius: 11, background: "var(--sunken)", border: "1px solid var(--rule)" }}>
      <Link href={hrefLs} className="tap" style={pill(house === "ls")}>Lok Sabha</Link>
      <Link href={hrefRs} className="tap" style={pill(house === "rs")}>Rajya Sabha</Link>
    </div>
  );
}
