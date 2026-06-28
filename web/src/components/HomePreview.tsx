import Link from "next/link";
import { getPersonResume, photoSrc } from "@/lib/api";
import { Frame, PhotoBox, PartyPill } from "@/components/ui";
import { WealthLine } from "@/components/resume/charts";
import { rupees, attendancePct } from "@/lib/format";

// A real legislator whose profile is shown as the homepage showcase. Override via env if IDs change.
const SHOWCASE_ID = Number(process.env.NEXT_PUBLIC_SHOWCASE_PERSON_ID ?? 376);

/** Live, non-interactive preview of the real resume UI, built from one MP's actual data. */
export async function HomePreview() {
  let resume = null;
  try {
    resume = await getPersonResume(SHOWCASE_ID);
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
    <div style={{ flex: 1, padding: "12px 14px", borderRight: "1px solid var(--rule)" }}>
      <div className="mono" style={{ fontSize: 15, fontWeight: 600, color: accent ? "var(--accent)" : "var(--ink)" }}>{value}</div>
      <div style={{ fontSize: 9.5, color: "var(--muted)", marginTop: 3, letterSpacing: "0.04em" }}>{label}</div>
    </div>
  );

  return (
    <section style={{ padding: "8px 48px 64px", maxWidth: 1080, margin: "0 auto", width: "100%" }}>
      <div className="mono" style={{ fontSize: 11, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--faint)", marginBottom: 16 }}>
        Every legislator gets a resume like this
      </div>
      <Frame url={`neta-resume.app/person/${resume.id}`}>
        <div style={{ padding: 22 }}>
          <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>
            <PhotoBox w={64} h={78} src={photoSrc(resume.id, resume.photo_url)} />
            <div style={{ minWidth: 0, flex: 1 }}>
              <div className="serif" style={{ fontSize: 24, fontWeight: 600, lineHeight: 1.05 }}>{resume.display_name}</div>
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

          <div style={{ display: "flex", marginTop: 18, border: "1px solid var(--rule)", borderRadius: 10, overflow: "hidden", background: "var(--card2)" }}>
            {tile("DECLARED ASSETS", rupees(latestAssets), true)}
            {tile("CRIMINAL CASES", String(resume.criminal_cases.length))}
            {tile("PARTY LABELS", String(resume.party_history.length))}
            <div style={{ flex: 1, padding: "12px 14px" }}>
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
