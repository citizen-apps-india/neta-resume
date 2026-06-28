import Link from "next/link";
import { ThemeToggle } from "@/components/ThemeToggle";
import { ReportDiscrepancyButton } from "@/components/ReportDiscrepancy";

function Logo({ size = 30 }: { size?: number }) {
  return (
    <span
      style={{
        display: "inline-flex", width: size, height: size, borderRadius: 7, overflow: "hidden",
        border: "1px solid var(--rule)", background: "#fff", flexShrink: 0,
      }}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/logo.svg" alt="Neta·Resume logo" width={size} height={size} style={{ display: "block" }} />
    </span>
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
