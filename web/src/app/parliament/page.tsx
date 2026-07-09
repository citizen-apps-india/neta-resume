import Link from "next/link";
import type { Metadata } from "next";
import { SiteHeader } from "@/components/SiteHeader";
import { Donut } from "@/components/resume/charts";
import { MinistryBars } from "@/components/MinistryBars";
import { PhotoBox } from "@/components/ui";
import { themeColor } from "@/lib/themes";
import { getParliamentStats, photoSrc, type ParliamentStats } from "@/lib/api";

export const revalidate = 3600;
export const metadata: Metadata = {
  title: "Parliament functioning · Neta·Resume",
  description: "What the 18th Lok Sabha is asking — questions by policy theme and ministry, and the most active members.",
};

const fmt = (n: number | undefined) => (n != null ? n.toLocaleString("en-IN") : "—");

const cardStyle: React.CSSProperties = { border: "1px solid var(--rule)", borderRadius: 12, background: "var(--card2)", padding: "clamp(16px,3vw,22px)" };
const headStyle: React.CSSProperties = { fontFamily: "'Bricolage Grotesque',sans-serif", fontSize: 15, fontWeight: 600 };

function Tile({ num, label, accent }: { num: string; label: string; accent?: boolean }) {
  return (
    <div style={cardStyle}>
      <div className="mono" style={{ fontSize: "clamp(22px,4vw,30px)", fontWeight: 700, color: accent ? "var(--accent)" : "var(--ink)", lineHeight: 1.05 }}>{num}</div>
      <div style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 6, letterSpacing: "0.02em" }}>{label}</div>
    </div>
  );
}

export default async function ParliamentPage() {
  let s: ParliamentStats | null = null;
  try {
    s = await getParliamentStats();
  } catch { /* API not up yet */ }

  const themes = s?.themes ?? [];
  const donut = themes.map((t) => ({ label: t.theme, value: t.count, color: themeColor(t.theme) }));
  const topMinistry = s?.top_ministries?.[0];

  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 1120, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 64px", width: "100%" }}>
        <div className="mono" style={{ fontSize: 11, letterSpacing: "0.08em", color: "var(--accent)", marginBottom: 10 }}>PARLIAMENT FUNCTIONING</div>
        <h1 className="serif" style={{ fontSize: "clamp(26px,5.5vw,34px)", fontWeight: 500, letterSpacing: "-0.02em", margin: "0 0 6px" }}>
          What the House is asking
        </h1>
        <p style={{ fontSize: 15, color: "var(--ink2)", margin: "0 0 18px", maxWidth: "64ch" }}>
          The {s?.house ?? "18th Lok Sabha"}, seen through its parliamentary questions — by policy area and ministry, and the members driving it. Every figure is read live from the official record.
        </p>

        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 26 }}>
          <Link href="/parliament/search" className="tap" style={{ fontSize: 13, fontWeight: 500, padding: "8px 15px", borderRadius: 8, textDecoration: "none", border: "1px solid var(--border)", background: "var(--card2)", color: "var(--ink)" }}>⌕ Search the record</Link>
          <Link href="/parliament/trends" className="tap" style={{ fontSize: 13, fontWeight: 500, padding: "8px 15px", borderRadius: 8, textDecoration: "none", border: "1px solid var(--border)", background: "var(--card2)", color: "var(--ink)" }}>See trends over time →</Link>
        </div>

        {!s ? (
          <p style={{ color: "var(--muted)" }}>Parliament data is loading…</p>
        ) : (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(150px,1fr))", gap: 12, marginBottom: 26 }}>
              <Tile num={fmt(s.total_questions)} label="Questions asked" accent />
              <Tile num={fmt(s.total_debates)} label="Debates participated in" />
              <Tile num={fmt(s.active_mps)} label="Members asking questions" />
              <Tile num={topMinistry?.ministry ?? "—"} label="Most-questioned ministry" />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "minmax(280px,1fr) minmax(280px,1.1fr)", gap: 18, alignItems: "start" }} className="nr-2col">
              <div style={cardStyle}>
                <div style={{ ...headStyle, marginBottom: 4 }}>By policy area</div>
                <p style={{ fontSize: 12.5, color: "var(--muted)", margin: "0 0 14px" }}>Share of questions across the seven policy themes.</p>
                <Donut segments={donut} centerNum={fmt(s.total_questions)} centerLabel="questions" size={150} />
              </div>

              <div style={cardStyle}>
                <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 4 }}>
                  <span style={headStyle}>Most-questioned ministries</span>
                  <Link href="/parliament/ministries" className="mono" style={{ fontSize: 11.5, color: "var(--accent-2)", textDecoration: "none" }}>See all →</Link>
                </div>
                <p style={{ fontSize: 12.5, color: "var(--muted)", margin: "0 0 14px" }}>Which departments the House scrutinises most.</p>
                <MinistryBars items={s.top_ministries} />
              </div>
            </div>

            <div style={{ ...cardStyle, marginTop: 18 }}>
              <div style={{ ...headStyle, marginBottom: 4 }}>Most active members</div>
              <p style={{ fontSize: 12.5, color: "var(--muted)", margin: "0 0 14px" }}>Top questioners this term. Missing ≠ inactive — rule-exempt members (ministers, the Speaker) don't table questions.</p>
              <div style={{ display: "grid", gap: 6 }}>
                {s.most_active.map((m, i) => (
                  <Link key={m.id} href={`/person/${m.id}`} className="tap" style={{ display: "flex", alignItems: "center", gap: 12, padding: "7px 8px", borderRadius: 8, textDecoration: "none", color: "var(--ink)" }}>
                    <span className="mono" style={{ fontSize: 12, color: "var(--faint)", width: 22, textAlign: "right" }}>{i + 1}</span>
                    <PhotoBox w={30} h={36} src={photoSrc(m.id, m.photo_url)} />
                    <span style={{ fontWeight: 500, fontSize: 14 }}>{m.display_name}</span>
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 11.5, color: "var(--muted)" }}>
                      <span style={{ width: 7, height: 7, borderRadius: 2, background: themeColor(m.top_theme) }} />{m.top_theme}
                    </span>
                    <span className="mono" style={{ marginLeft: "auto", fontSize: 13, fontWeight: 600 }}>{fmt(m.count)}<span style={{ color: "var(--muted)", fontWeight: 400 }}> Qs</span></span>
                  </Link>
                ))}
              </div>
            </div>
          </>
        )}
      </main>
    </>
  );
}
