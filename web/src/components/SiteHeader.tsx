import Link from "next/link";
import { ThemeToggle } from "@/components/ThemeToggle";
import { ReportDiscrepancyButton } from "@/components/ReportDiscrepancy";

function Logo({ size = 26 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <rect x="5" y="3" width="22" height="26" rx="2.5" fill="var(--ink)" />
      <path d="M20 3 L27 10 L20 10 Z" fill="var(--bg)" />
      <rect x="9" y="14" width="14" height="1.8" rx="0.9" fill="var(--bg)" />
      <rect x="9" y="18.5" width="14" height="1.8" rx="0.9" fill="var(--bg)" />
      <rect x="9" y="23" width="8" height="1.8" rx="0.9" fill="var(--accent)" />
    </svg>
  );
}

export function SiteHeader() {
  return (
    <header
      style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "16px 28px", borderBottom: "1px solid var(--rule)",
        background: "var(--panel)", position: "sticky", top: 0, zIndex: 20,
        backdropFilter: "blur(8px)",
      }}
    >
      <Link href="/" style={{ display: "flex", alignItems: "center", gap: 10, textDecoration: "none", color: "var(--ink)" }}>
        <Logo />
        <span className="serif" style={{ fontWeight: 600, fontSize: 18 }}>Neta·Resume</span>
      </Link>
      <nav style={{ display: "flex", alignItems: "center", gap: 22 }}>
        <Link className="navlink" href="/lok-sabha" style={{ fontSize: 13, color: "var(--ink2)" }}>Lok Sabha</Link>
        <Link className="navlink" href="/rajya-sabha" style={{ fontSize: 13, color: "var(--ink2)" }}>Rajya Sabha</Link>
        <Link className="navlink" href="/directory" style={{ fontSize: 13, color: "var(--ink2)" }}>Directory</Link>
        <ThemeToggle />
        <ReportDiscrepancyButton />
      </nav>
    </header>
  );
}
