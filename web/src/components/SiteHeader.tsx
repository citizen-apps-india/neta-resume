import Link from "next/link";
import { HeaderNav } from "@/components/HeaderNav";

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
        padding: "14px clamp(16px, 4vw, 28px)", borderBottom: "1px solid var(--rule)",
        background: "var(--panel)", position: "sticky", top: 0, zIndex: 20,
        backdropFilter: "blur(8px)",
      }}
    >
      <Link href="/" style={{ display: "flex", alignItems: "center", gap: 10, textDecoration: "none", color: "var(--ink)" }}>
        <Logo />
        <span className="serif" style={{ fontWeight: 600, fontSize: "clamp(16px, 4vw, 18px)" }}>Neta·Resume</span>
      </Link>
      <HeaderNav />
    </header>
  );
}
