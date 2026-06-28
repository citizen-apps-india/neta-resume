import { BrowseShell } from "@/components/BrowseShell";
import { listPersons, type PersonSummary } from "@/lib/api";

export const dynamic = "force-dynamic";
export const metadata = { title: "State Level" };

export default async function StateLevelPage() {
  let people: PersonSummary[] = [];
  let error = false;
  try {
    people = await listPersons({ limit: 2000, jurisdiction: "state" });
  } catch {
    error = true;
  }
  return (
    <BrowseShell
      title="State Level"
      intro="Members of India's state legislative assemblies — starting with Maharashtra. Pick a state, then filter by party or criminal record and sort by declared wealth or cases. State legislatures aren't covered by parliamentary attendance records, so that field reads '—'; wealth, cases and party still apply."
      people={people}
      scope="state"
      error={error}
    />
  );
}
