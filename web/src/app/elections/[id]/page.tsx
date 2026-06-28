import { notFound } from "next/navigation";
import { BrowseShell } from "@/components/BrowseShell";
import { getElections, listPersons, type PersonSummary } from "@/lib/api";
import { pretty } from "@/lib/format";

export const dynamic = "force-dynamic";

const LEVEL_LABEL: Record<string, string> = { national: "National", state: "State", municipal: "Municipal" };

export default async function ElectionResultsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const elections = await getElections().catch(() => []);
  const election = elections.find((e) => e.eci_election_id === id);
  // Only past elections with a resolved house have browsable winner results.
  if (!election || election.status !== "past" || !election.house) notFound();

  let people: PersonSummary[] = [];
  let error = false;
  try {
    people = await listPersons({ limit: 2000, house: election.house, revalidate: 0 });
  } catch {
    error = true;
  }

  const facts = [
    LEVEL_LABEL[election.level] ?? election.level,
    election.election_date ? pretty(election.election_date) : null,
    `${election.winner_count.toLocaleString("en-IN")} winners${election.seats ? ` of ${election.seats} seats` : ""}`,
  ].filter(Boolean).join(" · ");

  return (
    <BrowseShell
      title={election.name}
      intro={`${facts}. Browse the winners with the same comparable signals as the directory — party, declared wealth and criminal cases. Losing candidates and vote margins are coming next.`}
      people={people}
      scope="election"
      error={error}
    />
  );
}
