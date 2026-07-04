import { BrowseShell } from "@/components/BrowseShell";
import { loadBrowse } from "@/lib/browse";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Directory",
  description:
    "Search every Indian legislator — MPs and MLAs — by name, party or constituency. Declared wealth, " +
    "criminal cases, party switches and career, each fact sourced to the Election Commission.",
};

export default async function Directory({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const data = await loadBrowse(await searchParams);
  return (
    <BrowseShell
      title="Directory"
      intro="Every legislator on file, across both houses and the state assemblies. Search by name, party or constituency, then filter by party or criminal record and sort by wealth, cases or attendance. Any two people are comparable at a glance."
      scope="all"
      {...data}
    />
  );
}
