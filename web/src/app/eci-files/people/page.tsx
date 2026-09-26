import type { Metadata } from "next";
import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
import { SectionHero } from "@/components/parliament/SectionHero";
import { SectionNav } from "@/components/eci-files/SectionNav";
import { CommissionTenureChart } from "@/components/eci-files/CommissionTenureChart";
import { PersonCard } from "@/components/eci-files/PersonCard";
import { StateOfficerTable } from "@/components/eci-files/StateOfficerTable";
import { NamedPeopleList } from "@/components/eci-files/NamedPeopleList";
import { PhotoCredits } from "@/components/eci-files/PhotoCredits";
import { getEciPeople, getEciSelections, type EciPersonSummary, type EciSelections } from "@/lib/api";
import { personGroupMeta } from "@/lib/eci-files";

export const metadata: Metadata = {
  title: "People · ECI Files",
  description: "The commissioners, the officials under them and the state officers who run the rolls, 2019 to today.",
  robots: { index: false, follow: false },
};

const GROUP_ORDER = ["commission", "secretariat", "state", "named"] as const;

export default async function EciFilesPeoplePage() {
  let people: EciPersonSummary[] = [];
  let selectionsData: EciSelections | null = null;
  let failed = false;
  try {
    people = await getEciPeople();
    selectionsData = await getEciSelections().catch(() => null);
  } catch {
    failed = true;
  }

  const byGroup = {
    commission: people.filter((p) => p.group === "commission"),
    secretariat: people.filter((p) => p.group === "secretariat"),
    state: people.filter((p) => p.group === "state"),
    named: people.filter((p) => p.group === "named"),
  };

  const navItems = GROUP_ORDER.filter((g) => byGroup[g].length > 0).map((g) => ({
    id: g === "commission" ? "commission" : g === "secretariat" ? "secretariat" : g === "state" ? "state" : "named",
    label: personGroupMeta(g).heading,
    count: byGroup[g].length,
  }));

  const photoCredits = people
    .filter((p) => p.photo)
    .map((p) => ({ slug: p.slug, name: p.name, photo: p.photo! }));

  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 1080, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
        <SectionHero
          eyebrow="ECI FILES · PEOPLE"
          title="Who runs the Election Commission"
          subtitle="The commissioners, the officials under them and the state officers who run the rolls, 2019 to today. Every line has a source."
          backHref="/eci-files"
          backLabel="ECI Files"
        />

        {failed ? (
          <p style={{ color: "var(--muted)", padding: "24px 4px" }}>
            The record hasn&apos;t loaded — try again in a moment.
          </p>
        ) : people.length === 0 ? (
          <p style={{ color: "var(--muted)", padding: "24px 4px" }}>No one on record yet.</p>
        ) : (
          <>
            <SectionNav items={navItems} ariaLabel="Groups on this page" />

            {byGroup.commission.length > 0 && (
              <>
                <h2 className="serif" style={{ fontSize: 18, fontWeight: 600, margin: "0 0 6px" }}>Who ran the Commission</h2>
                <CommissionTenureChart people={byGroup.commission} selectionsData={selectionsData} />
              </>
            )}

            {byGroup.commission.length > 0 && (
              <section id="commission" style={{ marginBottom: 34 }}>
                <h2 className="serif" style={{ fontSize: 20, fontWeight: 600, margin: "0 0 4px" }}>{personGroupMeta("commission").heading}</h2>
                <p style={{ fontSize: 12.5, color: "var(--muted)", margin: "0 0 14px" }}>{personGroupMeta("commission").description}</p>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(min(260px, 100%), 1fr))", gap: 14 }}>
                  {byGroup.commission.map((p) => <PersonCard key={p.slug} p={p} variant="commission" />)}
                </div>
              </section>
            )}

            {byGroup.secretariat.length > 0 && (
              <section id="secretariat" style={{ marginBottom: 34 }}>
                <h2 className="serif" style={{ fontSize: 20, fontWeight: 600, margin: "0 0 4px" }}>{personGroupMeta("secretariat").heading}</h2>
                <p style={{ fontSize: 12.5, color: "var(--muted)", margin: "0 0 14px" }}>{personGroupMeta("secretariat").description}</p>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(min(230px, 100%), 1fr))", gap: 12 }}>
                  {byGroup.secretariat.map((p) => <PersonCard key={p.slug} p={p} variant="secretariat" />)}
                </div>
              </section>
            )}

            {byGroup.state.length > 0 && (
              <section id="state" style={{ marginBottom: 34 }}>
                <h2 className="serif" style={{ fontSize: 20, fontWeight: 600, margin: "0 0 4px" }}>{personGroupMeta("state").heading}</h2>
                <p style={{ fontSize: 12.5, color: "var(--muted)", margin: "0 0 14px" }}>{personGroupMeta("state").description}</p>
                <StateOfficerTable people={byGroup.state} />
              </section>
            )}

            {byGroup.named.length > 0 && (
              <section id="named" style={{ marginBottom: 20 }}>
                <h2 className="serif" style={{ fontSize: 20, fontWeight: 600, margin: "0 0 4px" }}>{personGroupMeta("named").heading}</h2>
                <p style={{ fontSize: 12.5, color: "var(--muted)", margin: "0 0 14px" }}>{personGroupMeta("named").description}</p>
                <NamedPeopleList people={byGroup.named} />
              </section>
            )}

            <PhotoCredits photos={photoCredits} />
          </>
        )}

        <div style={{ marginTop: 26, display: "flex", flexDirection: "column", gap: 6 }}>
          <Link href="/eci-files/selections" className="mono" style={{ fontSize: 12, color: "var(--accent-2)", textDecoration: "none" }}>
            How they were chosen →
          </Link>
          <Link href="/eci-files/entries" className="mono" style={{ fontSize: 12, color: "var(--accent-2)", textDecoration: "none" }}>
            ← Every entry
          </Link>
        </div>
      </main>
    </>
  );
}
