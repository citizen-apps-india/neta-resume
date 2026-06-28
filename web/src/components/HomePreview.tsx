import Link from "next/link";
import { headers } from "next/headers";
import { getPersonResume, listPersons, photoSrc } from "@/lib/api";
import { Frame, PhotoBox, PartyPill } from "@/components/ui";
import { WealthLine } from "@/components/resume/charts";
import { rupees, attendancePct } from "@/lib/format";
import { pointToConstituency, REGION_TO_STATE } from "@/lib/geo";

// Default MP shown when we can't resolve a location (local dev, unknown region). Override via env.
const DEFAULT_ID = Number(process.env.NEXT_PUBLIC_SHOWCASE_PERSON_ID ?? 376);

const titleCase = (s: string) => s.toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());

type Featured = { id: number; lead: string; place: string | null; precise: boolean };

/** Pick whom to feature from the visitor's approximate location (Vercel IP geo headers, no prompt). */
async function resolveFeatured(): Promise<Featured> {
  try {
    const h = await headers();
    const lat = parseFloat(h.get("x-vercel-ip-latitude") ?? "");
    const lng = parseFloat(h.get("x-vercel-ip-longitude") ?? "");
    // 1) Constituency-precise: IP lat/long → polygon → that constituency's MP.
    if (Number.isFinite(lat) && Number.isFinite(lng)) {
      const pc = pointToConstituency(lat, lng);
      if (pc) {
        const m = await listPersons({ constituency: pc, limit: 1 });
        if (m[0]) return { id: m[0].id, lead: "Your area’s MP", place: titleCase(m[0].constituency ?? pc), precise: true };
      }
    }
    // 2) State fallback: region code → a random Lok Sabha MP from that state.
    const region = h.get("x-vercel-ip-country-region");
    const state = region ? REGION_TO_STATE[region.toUpperCase()] : undefined;
    if (state) {
      const list = await listPersons({ state, limit: 80 });
      const ls = list.filter((p) => p.current_house === "Lok Sabha");
      const pool = ls.length ? ls : list;
      if (pool.length) {
        const pick = pool[Math.floor(Math.random() * pool.length)];
        return { id: pick.id, lead: "An MP from", place: state, precise: false };
      }
    }
  } catch {
    /* headers/geo unavailable (e.g. local dev) — fall through to default */
  }
  return { id: DEFAULT_ID, lead: "A sample resume", place: null, precise: false };
}

/** Live, non-interactive preview of the real resume UI, built from a nearby MP's actual data. */
export async function HomePreview() {
  const { id, lead, place, precise } = await resolveFeatured();
  let resume = null;
  try {
    resume = (await getPersonResume(id)) ?? (id !== DEFAULT_ID ? await getPersonResume(DEFAULT_ID) : null);
  } catch {
    return null;
  }
  if (!resume) return null;

  const pts = [...resume.wealth]
    .sort((a, b) => a.filed_year - b.filed_year)
    .map((w) => ({ label: w.election_cycle, value: w.total_assets }));
  const latestAssets = pts.length ? pts[pts.length - 1].value : null;
  const term = resume.office_terms.find((t) => t.status === "sitting") ?? resume.office_terms[0];
  const attendance = term?.attendance_pct ?? null;
  const tile = (label: string, value: string, accent = false) => (
    <div style={{ padding: "12px 14px" }}>
      <div className="mono" style={{ fontSize: 15, fontWeight: 600, color: accent ? "var(--accent)" : "var(--ink)" }}>{value}</div>
      <div style={{ fontSize: 9.5, color: "var(--muted)", marginTop: 3, letterSpacing: "0.04em" }}>{label}</div>
    </div>
  );

  return (
    <section style={{ padding: "8px clamp(16px,5vw,48px) 64px", maxWidth: 1080, margin: "0 auto", width: "100%" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0 }}>
          <span style={{ fontSize: 12.5, color: "var(--muted)" }}>{lead}</span>
          {place && (
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "4px 11px", borderRadius: 999, background: "var(--accent-soft)", color: "var(--accent-soft-fg)", fontSize: 12.5, fontWeight: 600 }}>
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: "currentColor" }} />
              {place}
            </span>
          )}
        </div>
        {precise && (
          <Link href="/directory" className="navlink" style={{ fontSize: 12, color: "var(--muted)" }}>
            Not you? Search →
          </Link>
        )}
      </div>
      <Frame url={`neta-resume.app/person/${resume.id}`}>
        <div style={{ padding: 22 }}>
          <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>
            <PhotoBox w={64} h={78} src={photoSrc(resume.id, resume.photo_url)} />
            <div style={{ minWidth: 0, flex: 1 }}>
              <div className="serif" style={{ fontSize: "clamp(20px,5vw,24px)", fontWeight: 600, lineHeight: 1.05 }}>{resume.display_name}</div>
              {resume.native_name && <div className="deva" style={{ fontSize: 13, color: "var(--muted)", marginTop: 2 }}>{resume.native_name}</div>}
              <div style={{ marginTop: 8, display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                {term?.party && <PartyPill party={term.party} />}
                {term && (
                  <span className="mono" style={{ fontSize: 10.5, color: "var(--muted)" }}>
                    {[term.house, term.constituency].filter(Boolean).join(" · ").toUpperCase()}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="nr-cells" style={{ gridTemplateColumns: "repeat(4,1fr)", marginTop: 18, border: "1px solid var(--rule)", borderRadius: 10, overflow: "hidden", background: "var(--card2)" }}>
            {tile("DECLARED ASSETS", rupees(latestAssets), true)}
            {tile("CRIMINAL CASES", String(resume.criminal_cases.length))}
            {tile("PARTY LABELS", String(resume.party_history.length))}
            <div style={{ padding: "12px 14px" }}>
              <div className="mono" style={{ fontSize: 15, fontWeight: 600 }}>{attendancePct(attendance)}</div>
              <div style={{ fontSize: 9.5, color: "var(--muted)", marginTop: 3, letterSpacing: "0.04em" }}>ATTENDANCE</div>
            </div>
          </div>

          {pts.length > 0 && (
            <div style={{ marginTop: 18 }}>
              <div className="mono" style={{ fontSize: 10, letterSpacing: "0.08em", color: "var(--muted)", marginBottom: 8 }}>
                DECLARED ASSETS, BY ELECTION CYCLE
              </div>
              <WealthLine points={pts} />
            </div>
          )}

          <div style={{ marginTop: 18, textAlign: "right" }}>
            <Link href={`/person/${resume.id}`} className="navlink" style={{ fontSize: 12.5, color: "var(--accent)" }}>
              See the full profile →
            </Link>
          </div>
        </div>
      </Frame>
    </section>
  );
}
