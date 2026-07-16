import { notFound } from "next/navigation";
import { BrowseShell } from "@/components/BrowseShell";
import { getElections } from "@/lib/api";
import { loadBrowse } from "@/lib/browse";
import { pretty } from "@/lib/format";

const LEVEL_LABEL: Record<string, string> = { national: "National", state: "State", municipal: "Municipal" };

export default async function ElectionResultsPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { id } = await params;
  const elections = await getElections().catch(() => []);
  const election = elections.find((e) => e.eci_election_id === id);
  // Only past elections with a resolved house have browsable winner results.
  if (!election || election.status !== "past" || !election.house) notFound();

  const data = await loadBrowse(await searchParams, { base: { house: election.house } });

  const facts = [
    LEVEL_LABEL[election.level] ?? election.level,
    election.election_date ? pretty(election.election_date) : null,
    `${election.winner_count.toLocaleString("en-IN")} winners${election.seats ? ` of ${election.seats} seats` : ""}`,
  ].filter(Boolean).join(" · ");

  return (
    <BrowseShell
      title={election.name}
      intro={`${facts}. Browse the winners with the same comparable signals as the directory — party, declared wealth and criminal cases. Losing candidates and vote margins are coming next.`}
      scope="election"
      {...data}
    />
  );
}
