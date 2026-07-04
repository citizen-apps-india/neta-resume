import { BrowseShell } from "@/components/BrowseShell";
import { listPersons, type PersonSummary } from "@/lib/api";

export const dynamic = "force-dynamic";
export const metadata = { title: "Municipal", description: "Municipal corporation members — the sourced public record of India’s city-level elected representatives." };

export default async function MunicipalPage() {
  let people: PersonSummary[] = [];
  let error = false;
  try {
    people = await listPersons({ limit: 10000, jurisdiction: "municipal", revalidate: 0 });
  } catch {
    error = true;
  }
  return (
    <BrowseShell
      title="Municipal"
      intro="Elected members of India's municipal bodies — starting with the Municipal Corporation of Delhi (MCD). Pick a corporation, then filter by party or criminal record and sort by declared wealth or cases. Local bodies aren't covered by attendance records, so that field reads '—'; wealth, cases and party still apply."
      people={people}
      scope="municipal"
      error={error}
      defaultCorporation="Delhi MCD"
    />
  );
}
