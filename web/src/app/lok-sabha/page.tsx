import { BrowseShell } from "@/components/BrowseShell";
import { listPersons, type PersonSummary } from "@/lib/api";

export const dynamic = "force-dynamic";
export const metadata = { title: "Lok Sabha", description: "Every sitting Lok Sabha MP — declared wealth, criminal cases, party switches and attendance, each fact sourced to the Election Commission. Search, filter and compare." };

export default async function LokSabhaPage() {
  let people: PersonSummary[] = [];
  let error = false;
  try {
    people = await listPersons({ limit: 2000, house: "Lok Sabha" });
  } catch {
    error = true;
  }
  return (
    <BrowseShell
      title="Lok Sabha"
      intro="The sitting members of the lower house, each elected from a constituency. Filter by party or criminal record, sort by declared wealth, cases or attendance — every card carries the same comparable signals."
      people={people}
      scope="ls"
      error={error}
    />
  );
}
