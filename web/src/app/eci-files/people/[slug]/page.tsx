import type { Metadata } from "next";
import { Suspense } from "react";
import { notFound } from "next/navigation";
import { SiteHeader } from "@/components/SiteHeader";
import { SectionNav } from "@/components/eci-files/SectionNav";
import { ProfileHeader } from "@/components/eci-files/ProfileHeader";
import { TenureBar } from "@/components/eci-files/TenureBar";
import { KeyFacts } from "@/components/eci-files/KeyFacts";
import { CareerTimeline } from "@/components/eci-files/CareerTimeline";
import { SelectedByBlock } from "@/components/eci-files/SelectedByBlock";
import { PanelSeatsBlock } from "@/components/eci-files/PanelSeatsBlock";
import { PersonEntrySections } from "@/components/eci-files/PersonEntrySections";
import { personEntrySectionCounts } from "@/lib/eci-person-sections";
import { StatusLegend } from "@/components/eci-files/StatusLegend";
import { LaneTimeline } from "@/components/eci-files/LaneTimeline";
import { EntryDrawer } from "@/components/eci-files/EntryDrawer";
import { EntryDetail } from "@/components/eci-files/EntryDetail";
import { CitationList } from "@/components/eci-files/CitationList";
import { getEciEntry, getEciPerson, getEciSelections, type EciPersonPage, type EciSelections } from "@/lib/api";
import { careerTimeline, loadEciItem, ECI_LOAD_FAILED_MESSAGE } from "@/lib/eci-files";

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

function timelineWindow(entries: { date: string | null }[]): { from: string; to: string } {
  const today = new Date().toISOString().slice(0, 10);
  const dated = entries.map((e) => e.date).filter((d): d is string => Boolean(d)).sort();
  if (dated.length === 0) return { from: "2019-01-01", to: today };
  const earliest = dated[0];
  let from = `${earliest.slice(0, 7)}-01`;
  if (from < "2019-01-01") from = "2019-01-01";
  const daysApart = (new Date(today).getTime() - new Date(from).getTime()) / 86400000;
  if (daysApart < 60) {
    const d = new Date(`${from}T00:00:00Z`);
    d.setUTCMonth(d.getUTCMonth() - 6);
    from = d.toISOString().slice(0, 10);
  }
  return { from, to: today };
}

async function EntryDrawerBody({ id, page, basePath }: { id: string; page: EciPersonPage; basePath: string }) {
  const inPage = page.entries.find((e) => e.id === id);
  const full = inPage ?? (await getEciEntry(id).catch(() => null));
  if (!full) return null;
  return (
    <EntryDrawer>
      <EntryDetail entry={full} basePath={basePath} />
    </EntryDrawer>
  );
}

export default async function EciFilesPersonPage({
  params, searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ entry?: string }>;
}) {
  const { slug } = await params;
  const { entry } = await searchParams;
  const result = await loadEciItem(() => getEciPerson(slug));
  if (result.status === "not_found") notFound();
  if (result.status === "error") {
    return (
      <>
        <SiteHeader />
        <main style={{ maxWidth: 1080, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
          <p style={{ color: "var(--muted)", padding: "24px 4px" }}>{ECI_LOAD_FAILED_MESSAGE}</p>
        </main>
      </>
    );
  }
  const page = result.data;

  const selectionsData: EciSelections | null = await getEciSelections().catch(() => null);
  const regimes = selectionsData?.regimes ?? [];

  const { person, entries, selections, entries_index } = page;
  const basePath = `/eci-files/people/${slug}`;
  const hasProfile = person.group !== "named";
  const career = person.profile ? careerTimeline(person.profile.details, person.tenure) : { dated: [], undated: [] };
  const careerCount = career.dated.length + career.undated.length;
  const education = person.profile && typeof person.profile.details.education === "string" ? person.profile.details.education : null;
  const tenureEnd = person.profile && typeof person.profile.details.tenure_end === "string" ? person.profile.details.tenure_end : null;
  const laneWindow = timelineWindow(entries);
  const sectionCounts = personEntrySectionCounts(entries);

  const hasAppointeeSelection = selections.some((s) => s.appointed.some((a) => a.person_slug === slug));
  const fallbackSelection = !hasProfile || hasAppointeeSelection
    ? undefined
    : (person.profile && typeof person.profile.details.selection === "string"
      ? { selection: person.profile.details.selection, sourceUrl: typeof person.profile.details.selection_source_url === "string" ? person.profile.details.selection_source_url : null }
      : undefined);
  // SelectedByBlock/PanelSeatsBlock both render nothing when they have no rows and no fallback — the
  // nav chip must agree, or it links to an empty section.
  const showSelectedByChip = hasProfile
    ? hasAppointeeSelection || fallbackSelection !== undefined
    : selections.length > 0;

  const navItems = [
    ...(hasProfile && careerCount > 0 ? [{ id: "career", label: "Career", count: careerCount }] : []),
    ...(showSelectedByChip ? [{ id: "selected-by", label: hasProfile ? "Selected by" : "Sat on selection panels" }] : []),
    { id: "timeline", label: "Timeline", count: entries.length },
    ...sectionCounts.filter((s) => s.count > 0),
    ...(person.profile && person.profile.citations.length > 0 ? [{ id: "sources", label: "Sources", count: person.profile.citations.length }] : []),
  ];

  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 1080, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
        <ProfileHeader
          name={person.name}
          photo={person.photo}
          role={person.role}
          service={person.service}
          group={person.group}
          current={person.current}
          showStatusChip={hasProfile}
        />

        {hasProfile && (
          <div style={{ marginBottom: 8 }}>
            <TenureBar tenure={person.tenure} showLabels />
            {tenureEnd && <p style={{ fontSize: 12.5, color: "var(--muted)", margin: "6px 0 0" }}>{tenureEnd}</p>}
          </div>
        )}

        {!hasProfile && (
          <p style={{ fontSize: 13.5, color: "var(--ink2)", margin: "0 0 16px" }}>
            No profile: this page lists the {entries.length} entr{entries.length === 1 ? "y" : "ies"} that name {person.name}.
          </p>
        )}

        {hasProfile && entries.length < 5 && careerCount <= 1 && (
          <p style={{ fontSize: 12.5, color: "var(--muted)", margin: "8px 0 16px" }}>
            The record has little on {person.name} so far: {entries.length} entr{entries.length === 1 ? "y" : "ies"} and {careerCount} career line{careerCount === 1 ? "" : "s"}.
          </p>
        )}

        {hasProfile && (
          <KeyFacts
            slug={slug}
            group={person.group}
            tenure={person.tenure}
            service={person.service}
            selections={selections}
            regimes={regimes}
            statusCounts={person.status_counts}
          />
        )}

        <SectionNav items={navItems} ariaLabel="On this page" />

        <div className="eci-profile-grid">
          {hasProfile && careerCount > 0 && (
            <section id="career" style={{ marginBottom: 30 }}>
              <h2 className="serif" style={{ fontSize: 20, fontWeight: 600, margin: "0 0 4px" }}>Career</h2>
              {education && <p style={{ fontSize: 12.5, color: "var(--muted)", margin: "0 0 12px" }}>Education: {education}</p>}
              <CareerTimeline dated={career.dated} undated={career.undated} />
            </section>
          )}

          <div id="selected-by" className="eci-rail">
            {hasProfile ? (
              <SelectedByBlock slug={slug} selections={selections} entriesIndex={entries_index} basePath={basePath} fallback={fallbackSelection} />
            ) : (
              <PanelSeatsBlock slug={slug} selections={selections} />
            )}
          </div>

          <section id="timeline" style={{ marginBottom: 30 }}>
            <h2 className="serif" style={{ fontSize: 20, fontWeight: 600, margin: "0 0 10px" }}>
              Timeline <span className="mono" style={{ fontSize: 13, color: "var(--faint)", fontWeight: 400 }}>{entries.length}</span>
            </h2>
            <div style={{ marginBottom: 10 }}><StatusLegend /></div>
            <LaneTimeline
              entries={entries}
              from={laneWindow.from}
              to={laneWindow.to}
              activeId={entry}
              hideEmptyLanes
            />
            {entry && (
              <Suspense fallback={null}>
                <EntryDrawerBody id={entry} page={page} basePath={basePath} />
              </Suspense>
            )}
          </section>

          <div>
            <PersonEntrySections name={person.name} entries={entries} />
          </div>

          {person.profile && (
            <section id="sources" style={{ marginBottom: 10 }}>
              <h2 className="serif" style={{ fontSize: 18, fontWeight: 600, margin: "0 0 10px" }}>
                Sources for this profile <span className="mono" style={{ fontSize: 12, color: "var(--faint)", fontWeight: 400 }}>{person.profile.citations.length}</span>
              </h2>
              <CitationList citations={person.profile.citations} />
            </section>
          )}
        </div>
      </main>
    </>
  );
}
