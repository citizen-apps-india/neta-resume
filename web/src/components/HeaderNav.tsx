"use client";

import Link from "next/link";
import { useState } from "react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { ReportDiscrepancyButton } from "@/components/ReportDiscrepancy";
import { ElectionsNav } from "@/components/ElectionsNav";

const LINKS: [string, string][] = [
  ["/lok-sabha", "Lok Sabha"],
  ["/rajya-sabha", "Rajya Sabha"],
  ["/state-level", "State Level"],
  ["/municipal", "Municipal"],
  ["/parliament", "Parliament"],
  ["/directory", "Directory"],
];

/** Header navigation: a desktop row, collapsing to a hamburger + dropdown panel on ≤820px. */
export function HeaderNav() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <nav className="nr-nav-desktop">
        {LINKS.map(([href, label]) => (
          <Link key={href} className="navlink" href={href} style={{ fontSize: 13, color: "var(--ink2)" }}>{label}</Link>
        ))}
        <ElectionsNav style={{ fontSize: 13, color: "var(--ink2)" }} />
        <ThemeToggle />
        <ReportDiscrepancyButton />
      </nav>

      <button
        className="nr-nav-burger tap"
        aria-label="Menu"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        style={{
          alignItems: "center", justifyContent: "center", width: 38, height: 38, borderRadius: 8,
          border: "1px solid var(--border)", background: "var(--card2)", color: "var(--ink)",
          fontSize: 17, cursor: "pointer",
        }}
      >
        {open ? "✕" : "☰"}
      </button>

      <div
        className={`nr-menu-panel${open ? " open" : ""}`}
        style={{
          position: "absolute", top: "100%", left: 0, right: 0, flexDirection: "column", gap: 14,
          padding: "16px 20px", background: "var(--panel)", borderBottom: "1px solid var(--rule)",
          boxShadow: "0 18px 32px -22px var(--shadow)",
        }}
      >
        {LINKS.map(([href, label]) => (
          <Link key={href} className="navlink" href={href} onClick={() => setOpen(false)} style={{ fontSize: 16, color: "var(--ink)" }}>
            {label}
          </Link>
        ))}
        <ElectionsNav onClick={() => setOpen(false)} style={{ fontSize: 16, color: "var(--ink)" }} />
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, marginTop: 4, flexWrap: "wrap" }}>
          <ThemeToggle />
          <ReportDiscrepancyButton />
        </div>
      </div>
    </>
  );
}
