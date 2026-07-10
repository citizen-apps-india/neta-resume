import Link from "next/link";
import type { Metadata } from "next";
import { SiteHeader } from "@/components/SiteHeader";
import { ParliamentSearchInput } from "@/components/ParliamentSearchInput";
import { HouseToggle } from "@/components/HouseToggle";
import { THEME_COLORS, themeColor } from "@/lib/themes";
import { searchRecords, docSrc, type House, type RecordHit } from "@/lib/api";

export const revalidate = 3600;
export const metadata: Metadata = {
  title: "Search the record · Parliament functioning · Neta·Resume",
  description: "Search the 18th Lok Sabha's questions and debates by topic — railways, MSP, health, and more.",
};

const PAGE = 30;
const THEMES = Object.keys(THEME_COLORS).filter((t) => t !== "Other");
const cardStyle: React.CSSProperties = { border: "1px solid var(--rule)", borderRadius: 12, background: "var(--card2)", padding: "clamp(14px,3vw,20px)" };

/** Build a /parliament/search URL with the given params merged over the current ones. */
function href(cur: { q?: string; kind?: string; theme?: string; house?: string }, patch: Record<string, string | undefined>): string {
  const merged = { ...cur, ...patch };
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(merged)) if (v) p.set(k, v);
  return `/parliament/search${p.toString() ? `?${p.toString()}` : ""}`;
}

function Pill({ label, active, to }: { label: string; active: boolean; to: string }) {
  return (
    <Link href={to} className="tap" style={{
      fontSize: 12.5, padding: "5px 13px", borderRadius: 20, textDecoration: "none",
      border: `1px solid ${active ? "var(--accent)" : "var(--rule)"}`,
      background: active ? "var(--accent-soft)" : "var(--card)",
      color: active ? "var(--accent-soft-fg)" : "var(--ink2)",
    }}>{label}</Link>
  );
}

function Hit({ h }: { h: RecordHit }) {
  const isQ = h.kind === "question";
  return (
    <div style={{ display: "grid", gap: 6, padding: "13px 2px", borderBottom: "1px solid var(--rule)" }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}>
        <span className="mono" style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.04em", padding: "2px 7px", borderRadius: 5, background: isQ ? "var(--accent-soft)" : "var(--rule)", color: isQ ? "var(--accent-soft-fg)" : "var(--ink2)" }}>
          {isQ ? "QUESTION" : "DEBATE"}
        </span>
        <span style={{ fontSize: 14.5, fontWeight: 500, color: "var(--ink)", flex: 1, minWidth: 220 }}>{h.title || "—"}</span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", fontSize: 12, color: "var(--muted)" }}>
        <Link href={`/person/${h.mp_id}`} style={{ color: "var(--ink2)", textDecoration: "none", fontWeight: 500 }}>{h.mp_name}</Link>
        {h.ministry && <span>· {h.ministry}</span>}
        {h.theme && (
          <span style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
            <span style={{ width: 7, height: 7, borderRadius: 2, background: themeColor(h.theme) }} />{h.theme}
          </span>
        )}
        {h.date && <span className="mono">· {h.date}</span>}
        <a href={docSrc(h.kind, h.id)} target="_blank" rel="noopener noreferrer" style={{ marginLeft: "auto", color: "var(--accent-2)", textDecoration: "none", fontSize: 11.5 }}>
          {isQ ? "reply →" : "text →"}
        </a>
      </div>
    </div>
  );
}

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; kind?: string; theme?: string; offset?: string; house?: string }>;
}) {
  const sp = await searchParams;
  const q = (sp.q ?? "").trim();
  const kind = sp.kind === "question" || sp.kind === "debate" ? sp.kind : undefined;
  const theme = sp.theme && THEMES.includes(sp.theme) ? sp.theme : undefined;
  const offset = Math.max(0, Number(sp.offset ?? 0) || 0);
  const house: House = sp.house === "rs" ? "rs" : "ls";
  const houseParam = house === "rs" ? "rs" : undefined;   // keep ?house out of LS (default) URLs
  const houseLabel = house === "rs" ? "Rajya Sabha" : "18th Lok Sabha";
  const cur = { q, kind, theme, house: houseParam };

  let items: RecordHit[] = [];
  let total = 0;
  let failed = false;
  if (q.length >= 2) {
    try {
      const r = await searchRecords({ q, kind, theme, limit: PAGE, offset, house });
      items = r.items;
      total = r.total;
    } catch { failed = true; }
  }

  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 900, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 64px", width: "100%" }}>
        <div style={{ marginBottom: 8 }}>
          <Link href={`/parliament${houseParam ? "?house=rs" : ""}`} className="mono" style={{ fontSize: 12, color: "var(--muted)", textDecoration: "none" }}>← Parliament functioning</Link>
        </div>
        <h1 className="serif" style={{ fontSize: "clamp(24px,5vw,32px)", fontWeight: 500, letterSpacing: "-0.02em", margin: "0 0 6px" }}>Search the record</h1>
        <p style={{ fontSize: 15, color: "var(--ink2)", margin: "0 0 20px", maxWidth: "64ch" }}>
          Search the {houseLabel}&rsquo;s questions and debates by topic. Each result links to the member and the official document.
        </p>

        <HouseToggle house={house} hrefLs={href(cur, { house: undefined, offset: undefined })} hrefRs={href(cur, { house: "rs", offset: undefined })} />

        <ParliamentSearchInput initial={q} kind={kind} theme={theme} house={houseParam} />

        {/* Kind filter */}
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 16 }}>
          <Pill label="All" active={!kind} to={href(cur, { kind: undefined, offset: undefined })} />
          <Pill label="Questions" active={kind === "question"} to={href(cur, { kind: "question", offset: undefined })} />
          <Pill label="Debates" active={kind === "debate"} to={href(cur, { kind: "debate", theme: undefined, offset: undefined })} />
        </div>
        {/* Theme filter (narrows to questions) */}
        <div style={{ display: "flex", gap: 7, flexWrap: "wrap", marginTop: 10 }}>
          <Pill label="All themes" active={!theme} to={href(cur, { theme: undefined, offset: undefined })} />
          {THEMES.map((t) => (
            <Pill key={t} label={t} active={theme === t} to={href(cur, { theme: t, kind: undefined, offset: undefined })} />
          ))}
        </div>

        <div style={{ marginTop: 22 }}>
          {q.length < 2 ? (
            <p style={{ color: "var(--muted)", padding: "24px 0" }}>Type a topic above to search — e.g. <em>railways</em>, <em>minimum support price</em>, <em>air pollution</em>.</p>
          ) : failed ? (
            <p style={{ color: "var(--muted)", padding: "24px 0" }}>Search is warming up — try again in a moment.</p>
          ) : total === 0 ? (
            <p style={{ color: "var(--muted)", padding: "24px 0" }}>No questions or debates match &ldquo;{q}&rdquo;{theme ? <> in {theme}</> : null}.</p>
          ) : (
            <>
              <div style={{ fontSize: 12.5, color: "var(--muted)", marginBottom: 4 }}>
                {total.toLocaleString("en-IN")} match{total === 1 ? "" : "es"} for &ldquo;{q}&rdquo;
                {kind ? <> · {kind === "question" ? "questions" : "debates"}</> : null}
                {theme ? <> · {theme}</> : null}
                {" "}· showing {offset + 1}–{Math.min(offset + PAGE, total)}
              </div>
              <div style={cardStyle}>
                {items.map((h) => <Hit key={`${h.kind}-${h.id}`} h={h} />)}
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: 16 }}>
                {offset > 0
                  ? <Link href={href(cur, { offset: String(Math.max(0, offset - PAGE)) })} className="mono" style={{ fontSize: 12.5, color: "var(--accent-2)", textDecoration: "none" }}>← Newer</Link>
                  : <span />}
                {offset + PAGE < total
                  ? <Link href={href(cur, { offset: String(offset + PAGE) })} className="mono" style={{ fontSize: 12.5, color: "var(--accent-2)", textDecoration: "none" }}>Older →</Link>
                  : <span />}
              </div>
            </>
          )}
        </div>
      </main>
    </>
  );
}
