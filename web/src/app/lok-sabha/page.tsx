import { BrowseShell } from "@/components/BrowseShell";
import { loadBrowse } from "@/lib/browse";

export const metadata = { title: "Lok Sabha", description: "Every sitting Lok Sabha MP — declared wealth, criminal cases, party switches and attendance, each fact sourced to the Election Commission. Search, filter and compare." };

export default async function LokSabhaPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const data = await loadBrowse(await searchParams, { base: { house: "Lok Sabha" } });
  return (
    <BrowseShell
      title="Lok Sabha"
      intro="The sitting members of the lower house, each elected from a constituency. Filter by party or criminal record, sort by declared wealth, cases or attendance — every card carries the same comparable signals."
      scope="ls"
      {...data}
    />
  );
}
