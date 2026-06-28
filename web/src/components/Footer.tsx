import Link from "next/link";

const REPO = "https://github.com/SahilSawant/neta-resume";

/** Site footer: public-interest / open-source statement + a plain-language data disclaimer. */
export function Footer() {
  return (
    <footer
      style={{
        borderTop: "1px solid var(--rule)",
        background: "var(--panel)",
        padding: "40px clamp(16px,5vw,28px) 48px",
      }}
    >
      <div style={{ maxWidth: 1080, margin: "0 auto", display: "grid", gap: 28 }}>
        <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", gap: 20 }}>
          <div style={{ maxWidth: "56ch" }}>
            <div className="serif" style={{ fontSize: 17, fontWeight: 600, marginBottom: 8 }}>
              Built in the public interest.
            </div>
            <p style={{ fontSize: 13, lineHeight: 1.6, color: "var(--ink2)", margin: 0 }}>
              Neta·Resume is a free, non-commercial, open-source project that assembles the public record
              of India&rsquo;s legislators in one place so any citizen can hold their representatives to
              account. The code and data pipeline are open for anyone to inspect, verify, and improve.
            </p>
            <Link
              href={REPO}
              className="navlink"
              style={{ display: "inline-block", marginTop: 12, fontSize: 12.5, color: "var(--accent)" }}
            >
              ↗ Source code on GitHub
            </Link>
          </div>
          <nav style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 13 }}>
            <Link className="navlink" href="/lok-sabha" style={{ color: "var(--ink2)" }}>Lok Sabha</Link>
            <Link className="navlink" href="/rajya-sabha" style={{ color: "var(--ink2)" }}>Rajya Sabha</Link>
            <Link className="navlink" href="/directory" style={{ color: "var(--ink2)" }}>Directory</Link>
          </nav>
        </div>

        <div
          className="mono"
          style={{
            fontSize: 11, lineHeight: 1.7, color: "var(--muted)", borderTop: "1px solid var(--rule)",
            paddingTop: 20, letterSpacing: "0.01em",
          }}
        >
          <strong style={{ color: "var(--ink2)" }}>Disclaimer.</strong> Figures are compiled from
          candidates&rsquo; own self-sworn affidavits to the Election Commission of India and other public
          records, with a source link on every fact. Criminal cases are <em>declared</em> and mostly{" "}
          <em>pending and unproven</em> — a listed case is an allegation, never a finding of guilt, and the
          severity tier shown is derived, not adjudicated. Wealth is as self-declared. Data may contain
          transcription or matching errors; spotted one?{" "}
          <span style={{ color: "var(--ink2)" }}>Use &ldquo;Report a discrepancy&rdquo; to flag it.</span>
        </div>

        <div style={{ fontSize: 11.5, color: "var(--faint)" }}>
          Neta·Resume · public-interest project · sources: Election Commission of India, sansad.in,
          MyNeta/ADR, PRS Legislative Research.
        </div>
      </div>
    </footer>
  );
}
