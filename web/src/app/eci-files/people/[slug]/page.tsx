import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { SiteHeader } from "@/components/SiteHeader";
import { SectionHero } from "@/components/parliament/SectionHero";
import { Timeline } from "@/components/eci-files/Timeline";
import { CitationList } from "@/components/eci-files/CitationList";
import { getEciPerson, getEciPeople } from "@/lib/api";
import { careerLines, detailLines, formatLooseDate, formatTenure } from "@/lib/eci-files";

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const page = await getEciPerson(slug).catch(() => null);
  const name = page?.person.name ?? "Person not found";
  return {
    title: `${name} · ECI Files`,
    description: `Sourced ECI Files record for ${name}.`,
    robots: { index: false, follow: false },
  };
}

export default async function EciFilesPersonPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const page = await getEciPerson(slug).catch(() => null);
  if (!page) notFound();

  const people = await getEciPeople().catch(() => []);
  const summary = people.find((p) => p.slug === slug);
  const profile = page.person.profile;
  const lines = profile ? detailLines(profile.details) : [];
  const career = profile ? careerLines(profile.details) : [];
  const tenure = formatTenure(summary?.tenure);

  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 900, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
        <SectionHero
          eyebrow="ECI FILES · PERSON"
          title={page.person.name}
          subtitle={
            <>
              {tenure.length > 0 ? tenure.join(" · ") : (summary?.role ?? "—")}
            </>
          }
          backHref="/eci-files/people"
          backLabel="People"
        />

        {profile ? (
          <section style={{ marginBottom: 30, border: "1px solid var(--rule)", borderRadius: 14, background: "var(--card2)", padding: "clamp(16px,3vw,22px)" }}>
            <p style={{ fontSize: 13.5, color: "var(--ink2)", lineHeight: 1.55, margin: "0 0 12px", maxWidth: "72ch" }}>
              {profile.summary}
            </p>
            {lines.length > 0 && (
              <dl style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(min(220px, 100%), 1fr))", gap: 10, margin: "0 0 14px" }}>
                {lines.map((l) => (
                  <div key={l.label}>
                    <dt className="mono" style={{ fontSize: 10, letterSpacing: "0.06em", color: "var(--faint)" }}>{l.label.toUpperCase()}</dt>
                    <dd style={{ margin: 0, fontSize: 13, color: "var(--ink)" }}>{l.value}</dd>
                  </div>
                ))}
              </dl>
            )}
            {career.length > 0 && (
              <div style={{ margin: "0 0 16px" }}>
                <div className="mono" style={{ fontSize: 9.5, letterSpacing: "0.06em", color: "var(--faint)", marginBottom: 6 }}>CAREER</div>
                <ol style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 8 }}>
                  {career.map((c, i) => (
                    <li key={i} style={{ display: "grid", gridTemplateColumns: "minmax(0, 150px) 1fr", gap: "2px 14px", fontSize: 13 }}>
                      <span className="mono" style={{ fontSize: 11.5, color: "var(--muted)", fontVariantNumeric: "tabular-nums" }}>
                        {c.from || c.to ? `${formatLooseDate(c.from)} – ${c.to ? formatLooseDate(c.to) : "—"}` : "—"}
                      </span>
                      <span style={{ color: "var(--ink)" }}>
                        {c.post}
                        {c.source_url && (
                          <>
                            {" "}
                            <a href={c.source_url} target="_blank" rel="noopener noreferrer" className="mono" style={{ fontSize: 10.5, color: "var(--accent)" }}>source ↗</a>
                          </>
                        )}
                      </span>
                    </li>
                  ))}
                </ol>
              </div>
            )}
            <div className="mono" style={{ fontSize: 9.5, letterSpacing: "0.06em", color: "var(--faint)", marginBottom: 6 }}>SOURCES</div>
            <CitationList citations={profile.citations} />
          </section>
        ) : (
          <p style={{ fontSize: 13, color: "var(--muted)", marginBottom: 24 }}>No standalone profile on record.</p>
        )}

        <h2 className="serif" style={{ fontSize: 18, fontWeight: 600, margin: "0 0 10px" }}>Timeline</h2>
        <Timeline entries={page.entries} />
      </main>
    </>
  );
}
