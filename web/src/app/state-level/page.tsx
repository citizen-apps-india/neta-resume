import { BrowseShell } from "@/components/BrowseShell";
import { listPersons, type PersonSummary } from "@/lib/api";

export const dynamic = "force-dynamic";
export const metadata = { title: "State Level", description: "Members of India’s state legislative assemblies (MLAs) — declared assets, criminal cases and party history, sourced and comparable, state by state." };

export default async function StateLevelPage() {
  let people: PersonSummary[] = [];
  let error = false;
  try {
    // revalidate: 0 — always reflect the live API (this list is small and changes rarely; avoids any
    // stale full-directory response getting cached during an API deploy).
    people = await listPersons({ limit: 2000, jurisdiction: "state", revalidate: 0 });
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
      defaultState="Maharashtra"
    />
  );
}
