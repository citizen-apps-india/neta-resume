import type { Metadata } from "next";
import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
import { SectionHero } from "@/components/parliament/SectionHero";
import { SectionNav } from "@/components/eci-files/SectionNav";
import { CommissionTenureChart } from "@/components/eci-files/CommissionTenureChart";
import { PersonTile } from "@/components/eci-files/people/PersonTile";
import { StateOfficerTable } from "@/components/eci-files/StateOfficerTable";
import { AlsoNamedPanel } from "@/components/eci-files/people/AlsoNamedPanel";
import { PhotoCredits } from "@/components/eci-files/PhotoCredits";
import { getEciPeople, type EciPersonSummary } from "@/lib/api";
import { personGroupMeta } from "@/lib/eci-files";

export const metadata: Metadata = {
  title: "People · ECI Files",
  description: "The commissioners, the officials under them and the state officers who run the rolls, 2019 to today.",
  robots: { index: false, follow: false },
};

const GROUP_ORDER = ["commission", "secretariat", "state", "named"] as const;

export default async function EciFilesPeoplePage() {
  let people: EciPersonSummary[] = [];
  let failed = false;
  try {
    people = await getEciPeople();
  } catch {
    failed = true;
  }

  const byGroup = {
    commission: people.filter((p) => p.group === "commission"),
    secretariat: people.filter((p) => p.group === "secretariat"),
    state: people.filter((p) => p.group === "state"),
    named: people.filter((p) => p.group === "named"),
  };
  const servingCount = byGroup.commission.filter((p) => p.current).length;

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
          title="Who has run the Commission, who runs it now"
          subtitle={`${byGroup.commission.length} commissioners since 2019, ${servingCount} serving today, one law that changed how they're chosen.`}
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

            {byGroup.commission.length > 0 && <CommissionTenureChart people={byGroup.commission} />}

            <div style={{ display: "flex", flexDirection: "column", gap: 32 }}>
              {byGroup.commission.length > 0 && (
                <section id="commission">
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 12 }}>
                    <h2 style={{ fontSize: 17, fontWeight: 650, margin: 0 }}>{personGroupMeta("commission").heading}</h2>
                    <span className="mono" style={{ fontSize: 11.5, color: "var(--muted)" }}>{byGroup.commission.length}</span>
                  </div>
                  <div className="eci-ptile-grid">
                    {byGroup.commission.map((p) => <PersonTile key={p.slug} p={p} size="commission" />)}
                  </div>
                </section>
              )}

              {byGroup.secretariat.length > 0 && (
                <section id="secretariat">
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 12 }}>
                    <h2 style={{ fontSize: 17, fontWeight: 650, margin: 0 }}>{personGroupMeta("secretariat").heading}</h2>
                    <span className="mono" style={{ fontSize: 11.5, color: "var(--muted)" }}>{byGroup.secretariat.length}</span>
                  </div>
                  <div className="eci-ptile-grid eci-ptile-grid--dense">
                    {byGroup.secretariat.map((p) => <PersonTile key={p.slug} p={p} size="compact" />)}
                  </div>
                </section>
              )}

              {byGroup.state.length > 0 && (
                <section id="state">
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 12 }}>
                    <h2 style={{ fontSize: 17, fontWeight: 650, margin: 0 }}>{personGroupMeta("state").heading}</h2>
                    <span className="mono" style={{ fontSize: 11.5, color: "var(--muted)" }}>{byGroup.state.length}</span>
                  </div>
                  <div className="eci-ptile-grid eci-ptile-grid--dense">
                    {byGroup.state.map((p) => (
                      <PersonTile key={p.slug} p={p} size="compact" roleOverride={`CEO, ${(p.role ?? "").replace(/^Chief Electoral Officer,\s*/, "") || "—"}`} />
                    ))}
                  </div>
                  <details className="eci-more" style={{ marginTop: 10 }}>
                    <summary className="mono" style={{ fontSize: 11.5, color: "var(--accent-2)", cursor: "pointer" }}>Show as a table</summary>
                    <div style={{ marginTop: 10 }}>
                      <StateOfficerTable people={byGroup.state} />
                    </div>
                  </details>
                </section>
              )}

              {byGroup.named.length > 0 && (
                <AlsoNamedPanel people={byGroup.named} />
              )}
            </div>

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
