import type { Metadata } from "next";
import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
import { SectionHero } from "@/components/parliament/SectionHero";
import { PersonCard } from "@/components/eci-files/PersonCard";
import { getEciPeople, type EciPersonSummary } from "@/lib/api";

export const metadata: Metadata = {
  title: "People · ECI Files",
  description: "Commissioners and officials named in the ECI Files record.",
  robots: { index: false, follow: false },
};

export default async function EciFilesPeoplePage() {
  let people: EciPersonSummary[] = [];
  let failed = false;
  try {
    people = await getEciPeople();
  } catch {
    failed = true;
  }

  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 900, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
        <SectionHero
          eyebrow="ECI FILES"
          title="People"
          subtitle="Commissioners and officials named in the record, each with their own sourced profile."
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
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(min(240px, 100%), 1fr))", gap: 14 }}>
              {people.filter((p) => p.role).map((p) => (
                <PersonCard key={p.slug} p={p} />
              ))}
            </div>
            {people.some((p) => !p.role) && (
              <section style={{ marginTop: 30 }}>
                <h2 className="serif" style={{ fontSize: 16, fontWeight: 600, margin: "0 0 10px" }}>Also named in the record</h2>
                <p style={{ fontSize: 12.5, color: "var(--muted)", margin: "0 0 10px" }}>
                  People who appear in entries but hold no Commission post covered here: judges, lawyers, ministers, party leaders.
                </p>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px 14px" }}>
                  {people.filter((p) => !p.role).map((p) => (
                    <Link key={p.slug} href={`/eci-files/people/${p.slug}`} style={{ fontSize: 13, color: "var(--accent)", textDecoration: "none" }}>
                      {p.name} <span className="mono" style={{ fontSize: 10.5, color: "var(--faint)" }}>{p.entry_count}</span>
                    </Link>
                  ))}
                </div>
              </section>
            )}
          </>
        )}
        <div style={{ marginTop: 22 }}>
          <Link href="/eci-files/entries" className="mono" style={{ fontSize: 12, color: "var(--accent-2)", textDecoration: "none" }}>
            ← Every entry
          </Link>
        </div>
      </main>
    </>
  );
}
