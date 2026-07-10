import Link from "next/link";
import type { Metadata } from "next";
import { SiteHeader } from "@/components/SiteHeader";
import { ParliamentSearchInput } from "@/components/ParliamentSearchInput";
import { HouseToggle } from "@/components/HouseToggle";
import { SectionHero } from "@/components/parliament/SectionHero";
import { SectionCard } from "@/components/parliament/SectionCard";
import { THEME_COLORS, themeColor } from "@/lib/themes";
import { searchRecords, docSrc, type House, type RecordHit } from "@/lib/api";

export const revalidate = 3600;
export const metadata: Metadata = {
  title: "Search the record · Parliament functioning · Neta·Resume",
  description: "Search Parliament's questions and debates by topic — railways, MSP, health, and more.",
};

const PAGE = 30;
const THEMES = Object.keys(THEME_COLORS).filter((t) => t !== "Other");

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
      background: active ? "var(--accent-soft)" : "var(--card2)",
      color: active ? "var(--accent-soft-fg)" : "var(--ink2)",
    }}>{label}</Link>
  );
}

function Hit({ h, first }: { h: RecordHit; first: boolean }) {
  const isQ = h.kind === "question";
  return (
    <div style={{ display: "grid", gap: 7, padding: "14px 4px", borderTop: first ? "none" : "1px solid var(--rule2)" }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 9, flexWrap: "wrap" }}>
        <span className="mono" style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: "0.05em", padding: "3px 8px", borderRadius: 6, background: isQ ? "var(--accent-soft)" : "var(--sunken)", color: isQ ? "var(--accent-soft-fg)" : "var(--muted)" }}>
          {isQ ? "QUESTION" : "DEBATE"}
        </span>
        <span style={{ fontSize: 14.5, fontWeight: 500, color: "var(--ink)", flex: 1, minWidth: 220, lineHeight: 1.35 }}>{h.title || "—"}</span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", fontSize: 12, color: "var(--muted)" }}>
        <Link href={`/person/${h.mp_id}`} className="navlink" style={{ color: "var(--ink2)", textDecoration: "none", fontWeight: 500 }}>{h.mp_name}</Link>
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
      <main style={{ maxWidth: 900, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
        <SectionHero
          eyebrow={`SEARCH · ${house === "rs" ? "RAJYA SABHA" : "18TH LOK SABHA"}`}
          title="Search the record"
          subtitle={<>Search the {houseLabel}&rsquo;s questions and debates by topic. Each result links to the member and the official document.</>}
          backHref={`/parliament${houseParam ? "?house=rs" : ""}`}
          right={<HouseToggle house={house} hrefLs={href(cur, { house: undefined, offset: undefined })} hrefRs={href(cur, { house: "rs", offset: undefined })} />}
        />

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
            <p style={{ color: "var(--muted)", padding: "24px 4px" }}>Type a topic above to search — e.g. <em>railways</em>, <em>minimum support price</em>, <em>air pollution</em>.</p>
          ) : failed ? (
            <p style={{ color: "var(--muted)", padding: "24px 4px" }}>Search is warming up — try again in a moment.</p>
          ) : total === 0 ? (
            <p style={{ color: "var(--muted)", padding: "24px 4px" }}>No questions or debates match &ldquo;{q}&rdquo;{theme ? <> in {theme}</> : null}.</p>
          ) : (
            <div className="fadeUp">
              <div style={{ fontSize: 12.5, color: "var(--muted)", margin: "0 2px 8px" }}>
                {total.toLocaleString("en-IN")} match{total === 1 ? "" : "es"} for &ldquo;{q}&rdquo;
                {kind ? <> · {kind === "question" ? "questions" : "debates"}</> : null}
                {theme ? <> · {theme}</> : null}
                {" "}· showing {offset + 1}–{Math.min(offset + PAGE, total)}
              </div>
              <SectionCard>
                {items.map((h, i) => <Hit key={`${h.kind}-${h.id}`} h={h} first={i === 0} />)}
              </SectionCard>
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: 16 }}>
                {offset > 0
                  ? <Link href={href(cur, { offset: String(Math.max(0, offset - PAGE)) })} className="mono" style={{ fontSize: 12.5, color: "var(--accent-2)", textDecoration: "none" }}>← Newer</Link>
                  : <span />}
                {offset + PAGE < total
                  ? <Link href={href(cur, { offset: String(offset + PAGE) })} className="mono" style={{ fontSize: 12.5, color: "var(--accent-2)", textDecoration: "none" }}>Older →</Link>
                  : <span />}
              </div>
            </div>
          )}
        </div>
      </main>
    </>
  );
}
