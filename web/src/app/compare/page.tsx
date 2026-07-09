import Link from "next/link";
import type { Metadata } from "next";
import { SiteHeader } from "@/components/SiteHeader";
import { getPersonResume, photoSrc, type PersonResume } from "@/lib/api";
import { PhotoBox, PartyPill } from "@/components/ui";
import { SegmentedBar } from "@/components/resume/policy-focus";
import { themeColor } from "@/lib/themes";

export const revalidate = 3600;
export const metadata: Metadata = { title: "Compare legislators · Neta·Resume" };

async function load(id: string | undefined): Promise<PersonResume | null> {
  const n = Number(id);
  return n ? getPersonResume(n) : null;
}

function Column({ r }: { r: PersonResume | null }) {
  if (!r) {
    return <div style={{ border: "1px dashed var(--rule)", borderRadius: 12, padding: 24, color: "var(--muted)", background: "var(--card2)" }}>Pick a legislator to compare.</div>;
  }
  const seat = r.office_terms?.[0];
  const focus = r.parliamentary_record?.thematic_focus ?? [];
  const qCount = r.parliamentary_record?.questions_count ?? null;
  return (
    <div style={{ border: "1px solid var(--rule)", borderRadius: 12, background: "var(--card2)", overflow: "hidden" }}>
      <div style={{ display: "flex", gap: 14, padding: 18 }}>
        <PhotoBox w={56} h={68} src={photoSrc(r.id, r.photo_url)} />
        <div style={{ minWidth: 0 }}>
          <Link href={`/person/${r.id}`} className="serif" style={{ fontSize: 19, fontWeight: 600, lineHeight: 1.15, color: "var(--ink)", textDecoration: "none" }}>{r.display_name}</Link>
          {r.native_name && <div className="deva" style={{ fontSize: 12.5, color: "var(--muted)", marginTop: 2 }}>{r.native_name}</div>}
          <div style={{ marginTop: 8, display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <PartyPill party={seat?.party ?? null} />
            {seat && <span className="mono" style={{ fontSize: 10.5, color: "var(--muted)" }}>{[seat.constituency, seat.house].filter(Boolean).join(" · ").toUpperCase()}</span>}
          </div>
        </div>
      </div>
      <div style={{ borderTop: "1px solid var(--rule)", padding: "16px 18px 20px" }}>
        <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 10 }}>
          <span style={{ fontFamily: "'Bricolage Grotesque',sans-serif", fontSize: 14, fontWeight: 600 }}>Policy focus</span>
          <span className="mono" style={{ fontSize: 11, color: "var(--faint)" }}>{qCount != null ? `${qCount} questions` : "no questions"}</span>
        </div>
        {focus.length === 0 ? (
          <div style={{ color: "var(--muted)", fontSize: 13 }}>No parliamentary questions on record.</div>
        ) : (
          <>
            <SegmentedBar focus={focus} />
            <div style={{ display: "grid", gap: 7, marginTop: 14 }}>
              {focus.map((t) => (
                <div key={t.theme} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12.5 }}>
                  <span style={{ width: 8, height: 8, borderRadius: 2, background: themeColor(t.theme), flexShrink: 0 }} />
                  <span style={{ color: "var(--ink2)" }}>{t.theme}</span>
                  <span className="mono" style={{ marginLeft: "auto", color: "var(--muted)" }}>{Math.round(t.share * 100)}%</span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default async function ComparePage({ searchParams }: { searchParams: Promise<{ a?: string; b?: string }> }) {
  const { a, b } = await searchParams;
  const [ra, rb] = await Promise.all([load(a), load(b)]);
  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 900, margin: "0 auto", padding: "clamp(20px,4vw,36px) clamp(16px,4vw,24px)" }}>
      <div style={{ marginBottom: 6 }}>
        <Link href="/directory" className="mono" style={{ fontSize: 12, color: "var(--muted)", textDecoration: "none" }}>← Directory</Link>
      </div>
      <h1 className="serif" style={{ fontSize: "clamp(22px,4vw,30px)", fontWeight: 600, margin: "0 0 4px" }}>Compare legislators</h1>
      <p style={{ color: "var(--muted)", fontSize: 14, margin: "0 0 22px" }}>Side-by-side policy focus — what each member raises in the House, by policy area.</p>
      <div className="nr-2col" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "clamp(12px,3vw,20px)", alignItems: "start" }}>
        <Column r={ra} />
        <Column r={rb} />
      </div>
      </main>
    </>
  );
}
