import type { Metadata } from "next";
import { Suspense } from "react";
import { notFound } from "next/navigation";
import { SiteHeader } from "@/components/SiteHeader";
import { SectionNav } from "@/components/eci-files/SectionNav";
import { ProfileHeader } from "@/components/eci-files/ProfileHeader";
import { KeyFacts } from "@/components/eci-files/KeyFacts";
import { CareerLine } from "@/components/eci-files/people/CareerLine";
import { FullCareerDisclosure } from "@/components/eci-files/people/FullCareerDisclosure";
import { SelectedByBlock } from "@/components/eci-files/SelectedByBlock";
import { PanelSeatsBlock } from "@/components/eci-files/PanelSeatsBlock";
import { PersonRecordList } from "@/components/eci-files/people/PersonRecordList";
import { EntryDrawer } from "@/components/eci-files/EntryDrawer";
import { EntryDetail } from "@/components/eci-files/EntryDetail";
import { getEciEntry, getEciPerson, getEciSelections, type EciPersonPage, type EciSelections } from "@/lib/api";
import { careerTimeline, loadEciItem, ECI_LOAD_FAILED_MESSAGE } from "@/lib/eci-files";

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const page = await getEciPerson(slug).catch(() => null);
  const name = page?.person.name ?? "Person not found";
  return {
    title: `${name} · ECI Files`,
    description: `Sourced ECI Files record for ${name}.`,
    };
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
    ...(showSelectedByChip ? [{ id: "selected-by", label: hasProfile ? "Selected by" : "Sat on selection panels" }] : []),
    ...(entries.length > 0 ? [{ id: "record", label: hasProfile ? "Objections and decisions" : "Entries", count: entries.length }] : []),
    ...(person.profile && (careerCount > 0 || person.profile.citations.length > 0) ? [{ id: "full-career", label: "Full career" }] : []),
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
        >
          {hasProfile && careerCount > 0 && <CareerLine dated={career.dated} undated={career.undated} />}
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
        </ProfileHeader>

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

        <SectionNav items={navItems} ariaLabel="On this page" />

        <div style={{ display: "flex", flexDirection: "column", gap: 30 }}>
          <div id="selected-by">
            {hasProfile ? (
              <SelectedByBlock slug={slug} selections={selections} entriesIndex={entries_index} basePath={basePath} fallback={fallbackSelection} />
            ) : (
              <PanelSeatsBlock slug={slug} selections={selections} />
            )}
          </div>

          <PersonRecordList entries={entries} basePath={basePath} />

          {entry && (
            <Suspense fallback={null}>
              <EntryDrawerBody id={entry} page={page} basePath={basePath} />
            </Suspense>
          )}

          {person.profile && (careerCount > 0 || person.profile.citations.length > 0) && (
            <div id="full-career">
              <FullCareerDisclosure education={education} dated={career.dated} undated={career.undated} citations={person.profile.citations} />
            </div>
          )}
        </div>
      </main>
    </>
  );
}
