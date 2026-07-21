import Link from "next/link";
import { headers } from "next/headers";
import { getPersonResume, listPersons, photoSrc, type PersonResume } from "@/lib/api";
import { PhotoBox, PartyPill } from "@/components/ui";
import { HomePreviewToggle, type PreviewPanel } from "@/components/HomePreviewToggle";
import { WealthLine } from "@/components/resume/charts";
import { rupees, attendancePct } from "@/lib/format";
import { pointToConstituency, pointToAssembly, REGION_TO_STATE } from "@/lib/geo";

// Default MP shown when we can't resolve a location (local dev, unknown region). Override via env.
const DEFAULT_ID = Number(process.env.NEXT_PUBLIC_SHOWCASE_PERSON_ID ?? 376);

const titleCase = (s: string) => s.toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());

type Featured = {
  id: number; lead: string; place: string | null; precise: boolean;
  // When we can pin the visitor to a point, the state assembly member for that spot too.
  mla?: { id: number; place: string | null };
};

/** Pick whom to feature from the visitor's approximate location (Vercel IP geo headers, no prompt). */
async function resolveFeatured(): Promise<Featured> {
  try {
    const h = await headers();
    const lat = parseFloat(h.get("x-vercel-ip-latitude") ?? "");
    const lng = parseFloat(h.get("x-vercel-ip-longitude") ?? "");
    // 1) Point-precise: IP lat/long → polygon → that constituency's MP, and the assembly segment's MLA.
    if (Number.isFinite(lat) && Number.isFinite(lng)) {
      const pc = pointToConstituency(lat, lng);
      if (pc) {
        const { items: m } = await listPersons({ constituency: pc, limit: 1 });
        if (m[0]) {
          const featured: Featured = { id: m[0].id, lead: "Your area’s MP", place: titleCase(m[0].constituency ?? pc), precise: true };
          // The MLA for the same point (state assembly constituency). Best-effort: a name/segment miss
          // just leaves the widget MP-only.
          const seg = pointToAssembly(lat, lng);
          if (seg) {
            const { items: a } = await listPersons({ jurisdiction: "state", state: seg.state, constituency: seg.ac, limit: 1 });
            if (a[0]) featured.mla = { id: a[0].id, place: titleCase(a[0].constituency ?? seg.ac) };
          }
          return featured;
        }
      }
    }
    // 2) State fallback: region code → a random Lok Sabha MP from that state (no specific MLA).
    const region = h.get("x-vercel-ip-country-region");
    const state = region ? REGION_TO_STATE[region.toUpperCase()] : undefined;
    if (state) {
      const { items: list } = await listPersons({ state, limit: 80 });
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

/** The inner resume card (photo, party, stat tiles, assets-by-cycle chart, profile link). Reused for
 *  both the MP and the MLA panel; sits inside the browser-frame rendered by HomePreviewToggle. */
function PreviewCard({ resume }: { resume: PersonResume }) {
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
  );
}

/** Live, non-interactive preview of the real resume UI, built from the visitor's nearby MP (and, when we
 *  can pin the point, their state MLA too — shown via a toggle). */
export async function HomePreview() {
  const featured = await resolveFeatured();
  let resume: PersonResume | null = null;
  try {
    resume = (await getPersonResume(featured.id)) ?? (featured.id !== DEFAULT_ID ? await getPersonResume(DEFAULT_ID) : null);
  } catch {
    return null;
  }
  if (!resume) return null;

  const panels: PreviewPanel[] = [
    { key: "mp", tab: "Lok Sabha MP", lead: featured.lead, place: featured.place, url: `neta-resume.app/person/${resume.id}`, card: <PreviewCard resume={resume} /> },
  ];

  // Add the MLA panel only when we resolved one for the visitor's point.
  if (featured.mla) {
    try {
      const mlaResume = await getPersonResume(featured.mla.id);
      if (mlaResume) {
        panels.push({
          key: "mla", tab: "State MLA", lead: "Your area’s MLA", place: featured.mla.place,
          url: `neta-resume.app/person/${mlaResume.id}`, card: <PreviewCard resume={mlaResume} />,
        });
      }
    } catch {
      /* MLA resume unavailable — keep the widget MP-only */
    }
  }

  return (
    <section style={{ padding: "8px clamp(16px,5vw,48px) 64px", maxWidth: 1080, margin: "0 auto", width: "100%" }}>
      <HomePreviewToggle panels={panels} precise={featured.precise} />
    </section>
  );
}
