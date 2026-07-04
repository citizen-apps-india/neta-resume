import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
import { SearchBox } from "@/components/SearchBox";
import { HomePreview } from "@/components/HomePreview";
import { VisitorCount } from "@/components/VisitorCount";
import { getStats, type Stats } from "@/lib/api";

export const dynamic = "force-dynamic";

const FEATURES = [
  { icon: "₹", title: "Wealth declared", body: "Assets, liabilities and income from the candidate's own ECI affidavits — every cycle, side by side." },
  { icon: "§", title: "Cases pending", body: "Criminal cases with IPC/BNS sections and a severity tier. Always pending-vs-convicted; never a verdict." },
  { icon: "⇄", title: "Parties switched", body: "Every party held over a career, with when each stint began and ended — by the public record." },
  { icon: "⌂", title: "Offices held", body: "The full posting history across the Lok Sabha, Rajya Sabha and state legislatures, over time." },
];

export default async function Home() {
  let s: Stats | null = null;
  try {
    s = await getStats();
  } catch {
    /* API not up yet — render the page without live stats */
  }
  const fmt = (n: number | undefined) => (n ? n.toLocaleString("en-IN") : "—");
  const total = s?.total_legislators ?? 0;

  const stats = [
    { num: fmt(s?.total_legislators), label: "Legislators on file (growing)" },
    { num: fmt(s?.with_cases), label: "With declared criminal cases" },
    { num: fmt(s?.crorepatis), label: "Declaring assets over ₹1 crore" },
    { num: "100%", label: "Sourced to public records" },
  ];

  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "WebSite",
        name: "Neta·Resume",
        url: "https://neta-resume.app",
        description:
          "The sourced public record of every Indian legislator — wealth, criminal cases, party switches and career.",
        potentialAction: {
          "@type": "SearchAction",
          target: "https://neta-resume.app/directory?q={search_term_string}",
          "query-input": "required name=search_term_string",
        },
      },
      {
        "@type": "Organization",
        name: "Neta·Resume",
        url: "https://neta-resume.app",
        logo: "https://neta-resume.app/logo.svg",
      },
    ],
  };

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <SiteHeader />

      {/* hero */}
      <section style={{ position: "relative", padding: "clamp(44px,7vw,72px) clamp(16px,5vw,48px) clamp(40px,6vw,56px)", overflow: "hidden", borderBottom: "1px solid var(--rule)" }}>
        <div style={{ position: "absolute", inset: 0, backgroundImage: "linear-gradient(var(--gridline) 1px,transparent 1px)", backgroundSize: "100% 34px", opacity: 0.5, pointerEvents: "none" }} />
        <div style={{ position: "relative", maxWidth: 720, margin: "0 auto" }}>
          <div className="mono fadeUp" style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: 11, letterSpacing: "0.1em", color: "var(--accent)", marginBottom: 22 }}>
            <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--ok)", animation: "nrPulse 2s infinite" }} />
            UPDATED AFTER EVERY ELECTION &amp; AFFIDAVIT
          </div>
          <h1 className="serif fadeUp" style={{ fontSize: "clamp(34px,7vw,62px)", fontWeight: 500, lineHeight: 1.04, letterSpacing: "-0.025em", margin: "0 0 22px", textWrap: "balance" }}>
            Know exactly who represents you.
          </h1>
          <p className="fadeUp" style={{ fontSize: "clamp(15px,3.6vw,18px)", lineHeight: 1.55, color: "var(--ink2)", margin: "0 0 30px", maxWidth: "54ch" }}>
            The full public record of every legislator in India — wealth declared, cases pending, parties switched —
            sourced to the Election Commission and shown without spin.
          </p>
          <div className="fadeUp" style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "stretch" }}>
            <div style={{ minWidth: 200, maxWidth: 440, flex: 1, display: "flex" }}>
              <SearchBox big placeholder="Search by name, constituency or party…" />
            </div>
            <Link href="/directory" className="btnDark" style={{ display: "inline-flex", alignItems: "center", fontFamily: "'Bricolage Grotesque',sans-serif", fontSize: 14.5, fontWeight: 600, padding: "13px 24px", borderRadius: 10, border: "none", background: "var(--btn-bg)", color: "var(--btn-fg)", cursor: "pointer", textDecoration: "none" }}>
              View all{total ? ` ${total}` : ""} →
            </Link>
          </div>
          <div className="fadeUp" style={{ marginTop: 16 }}>
            <VisitorCount />
          </div>
        </div>
      </section>

      {/* stats strip */}
      <section className="nr-cells" style={{ gridTemplateColumns: "repeat(4,1fr)", borderBottom: "1px solid var(--rule)", maxWidth: 1080, margin: "0 auto", width: "100%" }}>
        {stats.map((s, i) => (
          <div key={i} style={{ padding: "clamp(16px,4vw,22px) clamp(14px,4vw,26px)" }}>
            <div className="mono" style={{ fontSize: "clamp(22px,5vw,28px)", fontWeight: 500, letterSpacing: "-0.02em" }}>{s.num}</div>
            <div style={{ fontSize: 12.5, color: "var(--muted)", marginTop: 6 }}>{s.label}</div>
          </div>
        ))}
      </section>

      {/* live preview of the real resume UI */}
      <HomePreview />

      {/* features */}
      <section style={{ padding: "clamp(32px,5vw,44px) clamp(16px,5vw,48px) clamp(48px,7vw,72px)", maxWidth: 1080, margin: "0 auto", width: "100%" }}>
        <div className="mono" style={{ fontSize: 11, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--faint)", marginBottom: 24 }}>
          What every file tells you
        </div>
        <div className="nr-2col" style={{ ["--cols" as string]: "1fr 1fr", ["--gap" as string]: "16px" }}>
          {FEATURES.map((f) => (
            <div key={f.title} className="liftsm" style={{ display: "flex", gap: 16, border: "1px solid var(--rule)", borderRadius: 12, background: "var(--card2)", padding: 24 }}>
              <div className="serif" style={{ width: 44, height: 44, borderRadius: 10, flexShrink: 0, background: "var(--accent-soft)", color: "var(--accent-soft-fg)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 22, fontWeight: 600 }}>
                {f.icon}
              </div>
              <div>
                <div className="serif" style={{ fontSize: 18, fontWeight: 600, lineHeight: 1.2 }}>{f.title}</div>
                <div style={{ fontSize: 13.5, color: "var(--muted)", lineHeight: 1.5, marginTop: 7 }}>{f.body}</div>
              </div>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
