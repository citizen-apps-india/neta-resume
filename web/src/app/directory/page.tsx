import { BrowseShell } from "@/components/BrowseShell";
import { listPersons, type PersonSummary } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function Directory({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; house?: string }>;
}) {
  const { q } = await searchParams;
  let people: PersonSummary[] = [];
  let error = false;
  try {
    people = await listPersons(2000);
  } catch {
    error = true;
  }
  return (
    <BrowseShell
      title="Directory"
      intro="Every legislator on file, across both houses. Search by name, party or constituency, then filter by party or criminal record and sort by wealth, cases or attendance. Any two people are comparable at a glance."
      people={people}
      scope="all"
      error={error}
      initialQuery={q ?? ""}
    />
  );
}
