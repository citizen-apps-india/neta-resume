import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { getPersonResume, photoSrc, type PersonResume } from "@/lib/api";
import { rupees, attendancePct, attendanceColor } from "@/lib/format";
import { SiteHeader } from "@/components/SiteHeader";
import { Frame, PhotoBox, PartyPill } from "@/components/ui";
import { ProfileTabs } from "@/components/resume/ProfileTabs";
import { ReportDiscrepancyButton } from "@/components/ReportDiscrepancy";

export const dynamic = "force-dynamic";

const SITE = "https://neta-resume.app";

/** The current party for a resume: the flagged-current affiliation, else the latest term's party. */
function currentPartyOf(r: PersonResume): string | null {
  return r.party_history?.find((p) => p.is_current)?.party ?? r.office_terms[0]?.party ?? null;
}

// Per-legislator title + description so an exact full-name search resolves to this page (the layout title
// template renders it as "<name> — <party>, <house> · Neta·Resume", name first).
export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  const r = await getPersonResume(Number(id)).catch(() => null);
  if (!r) return { title: "Legislator not found", robots: { index: false, follow: true } };
  const lead = r.office_terms[0];
  const party = currentPartyOf(r);
  const suffix = [party, lead?.house].filter(Boolean).join(", ");
  const title = suffix ? `${r.display_name} — ${suffix}` : r.display_name;
  const where = lead?.constituency ? ` (${lead.constituency})` : "";
  const description =
    `${r.display_name}${where}: declared assets, criminal cases, party switches, attendance and full ` +
    `career — every fact sourced to the Election Commission. Free public record on Neta·Resume.`;
  const canonical = `/person/${id}`;
  return {
    title,
    description,
    alternates: { canonical },
    openGraph: { title: `${title} · Neta·Resume`, description, url: `${SITE}${canonical}`, type: "profile" },
    twitter: { card: "summary_large_image", title: `${title} · Neta·Resume`, description },
  };
}

export default async function PersonPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const resume = await getPersonResume(Number(id));
  if (!resume) notFound();

  const lead = resume.office_terms[0];
  const latestAssets = [...resume.wealth].sort((a, b) => b.filed_year - a.filed_year)[0];
  const pending = resume.criminal_cases.filter((c) => !c.is_convicted).length;
  const convictions = resume.criminal_cases.filter((c) => c.is_convicted).length;
  const parties = new Set([
    ...resume.party_history.map((p) => p.party),
    ...resume.office_terms.map((o) => o.party).filter(Boolean),
  ]);
  const currentParty =
    resume.party_history.find((p) => p.is_current)?.party ?? lead?.party ?? null;
  // RS members file no ECI candidate affidavit, so we have no wealth/criminal data for them.
  // Show "—" rather than "0", which would falsely imply a clean record.
  const hasAffidavit = resume.wealth.length > 0;
  // Cumulative attendance % for the current term (PRS). Null = rule-exempt (minister/Speaker/LoP) or
  // not on record — shown as "—", never 0.
  const attendance = lead?.attendance_pct ?? null;
  const houseTag = lead ? `${lead.house.replace(/[^A-Z]/g, "") || "LS"}-${lead.cycle_number}` : "";
  // Individual questions this MP asked (PRS enumeration). Null record = not on record -> "—", never 0.
  const pRecord = resume.parliamentary_record;

  const metrics = [
    { label: "Declared net assets", src: latestAssets ? `ECI · ${latestAssets.election_cycle}` : "NO AFFIDAVIT", value: rupees(latestAssets?.total_assets ?? null), color: "var(--ink)", dot: "" },
    { label: "Pending criminal cases", src: hasAffidavit ? "ECI AFFIDAVIT" : "NO AFFIDAVIT", value: hasAffidavit ? String(pending) : "—", color: !hasAffidavit ? "var(--muted)" : pending ? "var(--sev2)" : "var(--ok)", dot: hasAffidavit && pending ? "var(--sev2)" : hasAffidavit ? "var(--ok)" : "" },
    { label: "Convictions on record", src: hasAffidavit ? "COURT / AFFIDAVIT" : "NO AFFIDAVIT", value: hasAffidavit ? String(convictions) : "—", color: convictions ? "var(--sev1)" : "var(--ink)", dot: "" },
    { label: "House attendance", src: attendance != null ? `PRS · ${houseTag}` : "NO RECORD", value: attendancePct(attendance), color: attendanceColor(attendance), dot: "" },
    { label: "Questions asked", src: pRecord ? `PRS · ${houseTag}` : "NO RECORD", value: pRecord ? String(pRecord.questions_count) : "—", color: pRecord ? "var(--ink)" : "var(--muted)", dot: "" },
    { label: "Party labels held", src: "PUBLIC RECORD", value: String(parties.size), color: "var(--ink)", dot: "" },
  ];

  const url = `neta-resume.app / person / ${slug(resume.display_name)}`;

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Person",
    name: resume.display_name,
    ...(resume.native_name ? { alternateName: resume.native_name } : {}),
    ...(lead?.house ? { jobTitle: `Member of ${lead.house}` } : {}),
    ...(currentParty ? { affiliation: { "@type": "Organization", name: currentParty } } : {}),
    ...(lead?.constituency ? { homeLocation: { "@type": "Place", name: lead.constituency } } : {}),
    ...(photoSrc(resume.id, resume.photo_url) ? { image: photoSrc(resume.id, resume.photo_url) } : {}),
    url: `${SITE}/person/${resume.id}`,
  };

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <SiteHeader />
      <main style={{ maxWidth: 1080, margin: "0 auto", padding: "24px clamp(14px,4vw,28px) 72px", width: "100%" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 16 }}>
          <Link href="/directory" className="navlink mono" style={{ fontSize: 11, color: "var(--muted)", textDecoration: "none" }}>
            ← Directory
          </Link>
          <ReportDiscrepancyButton
            variant="ghost"
            label="Report a discrepancy"
            prefill={`${resume.display_name} (#${resume.id})`}
          />
        </div>

        <Frame url={url}>
          {/* editorial hero */}
          <div className="nr-split" style={{ borderBottom: "1px solid var(--rule)" }}>
            <div style={{ minWidth: 0, padding: "clamp(24px,5vw,38px) clamp(18px,5vw,40px)", borderRight: "1px solid var(--rule)" }}>
              <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
                <PhotoBox w={108} h={128} label="OFFICIAL PHOTO" src={photoSrc(resume.id, resume.photo_url)} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="mono" style={{ fontSize: 10, letterSpacing: "0.12em", color: "var(--accent)", marginBottom: 10 }}>
                    FILE · {lead ? `${lead.house.replace(/[^A-Z]/g, "") || "LS"}-${lead.cycle_number}` : "—"} · #{resume.id}
                  </div>
                  <h1 className="serif" style={{ fontSize: "clamp(28px,6vw,42px)", fontWeight: 600, letterSpacing: "-0.02em", lineHeight: 1.02, margin: 0 }}>
                    {resume.display_name}
                  </h1>
                  {resume.native_name && (
                    <div className="deva" style={{ fontSize: "clamp(15px,4vw,18px)", color: "var(--muted)", marginTop: 4 }}>{resume.native_name}</div>
                  )}
                  <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 9, marginTop: 16 }}>
                    <PartyPill party={currentParty} />
                    {lead && <Meta>{lead.membership_type === "nominated" ? "Nominated" : "MP"} · {lead.house}</Meta>}
                    {(lead?.constituency ?? lead?.state) && <><Sep /><Meta>{lead?.constituency ?? lead?.state}</Meta></>}
                    {resume.age != null && <><Sep /><Meta>Age {resume.age}</Meta></>}
                    <Sep />
                    <Meta>{resume.office_terms.length} term{resume.office_terms.length === 1 ? "" : "s"} on file</Meta>
                  </div>
                  {resume.education && (
                    <div className="mono" style={{ fontSize: 10.5, color: "var(--faint)", letterSpacing: "0.04em", marginTop: 10 }}>
                      EDUCATION · {resume.education}
                    </div>
                  )}
                </div>
              </div>
              <p className="serif" style={{ fontSize: "clamp(15px,4vw,18px)", lineHeight: 1.55, color: "var(--ink2)", margin: "24px 0 0", maxWidth: "62ch" }}>
                {summary(resume, latestAssets?.total_assets ?? null, pending, convictions, parties.size)}
              </p>
            </div>

            {/* hero metrics */}
            <div style={{ display: "flex", flexDirection: "column" }}>
              {metrics.map((m, i) => (
                <div key={i} style={{ flex: 1, padding: "clamp(14px,3.5vw,18px) clamp(16px,4vw,26px)", borderBottom: i < metrics.length - 1 ? "1px solid var(--rule)" : "none", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
                  <div>
                    <div style={{ fontSize: 11.5, color: "var(--muted)" }}>{m.label}</div>
                    <div className="mono" style={{ fontSize: 9, color: "var(--faint)", letterSpacing: "0.06em", marginTop: 4 }}>{m.src}</div>
                  </div>
                  <div className="mono" style={{ fontSize: "clamp(19px,5vw,24px)", fontWeight: 500, letterSpacing: "-0.02em", color: m.color, display: "flex", alignItems: "center", gap: 8 }}>
                    {m.dot && <span style={{ width: 9, height: 9, borderRadius: 3, background: m.dot }} />}
                    {m.value}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <ProfileTabs resume={resume} />
        </Frame>

        <div style={{ display: "flex", gap: 9, alignItems: "flex-start", fontSize: 11.5, color: "var(--muted)", lineHeight: 1.5, marginTop: 20, maxWidth: "80ch" }}>
          <span className="mono" style={{ color: "var(--accent)", flexShrink: 0 }}>i</span>
          <span>
            Criminal cases are as declared in the candidate's own ECI affidavit and are mostly <strong style={{ color: "var(--ink2)" }}>pending and unproven</strong>.
            This file asserts no guilt. Every figure links to its source.
          </span>
        </div>
      </main>
    </>
  );
}

function summary(r: PersonResume, assets: number | null, pending: number, convictions: number, nParties: number): string {
  const lead0 = r.office_terms[0];
  const seat = lead0?.constituency ?? lead0?.state;
  const bits: string[] = [];
  bits.push(`${r.display_name} ${seat ? `represents ${seat}${lead0?.state && !lead0?.constituency ? " in the Rajya Sabha" : ""}` : "is on the public record"}.`);
  if (r.wealth.length === 0) {
    bits.push("No ECI candidate affidavit is on record, so declared wealth and cases are not available.");
  } else {
    if (assets != null) bits.push(`Declared assets stand at ${rupees(assets)}.`);
    if (r.criminal_cases.length === 0) bits.push("No criminal cases are declared.");
    else bits.push(`${r.criminal_cases.length} criminal case${r.criminal_cases.length === 1 ? "" : "s"} ${pending ? `(${pending} pending` : ""}${convictions ? `, ${convictions} convicted)` : pending ? ")" : ""} appear on the affidavit.`);
  }
  bits.push(`${nParties} party label${nParties === 1 ? "" : "s"} on file.`);
  return bits.join(" ");
}

function slug(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function Meta({ children }: { children: React.ReactNode }) {
  return <span style={{ fontSize: 13, color: "var(--ink2)" }}>{children}</span>;
}
function Sep() {
  return <span style={{ width: 4, height: 4, borderRadius: "50%", background: "var(--border2)" }} />;
}
