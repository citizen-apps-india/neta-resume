import { BrowseShell } from "@/components/BrowseShell";
import { loadBrowse } from "@/lib/browse";

export const metadata = { title: "Municipal", description: "Municipal corporation members — the sourced public record of India’s city-level elected representatives." };

export default async function MunicipalPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const data = await loadBrowse(await searchParams, { base: { jurisdiction: "municipal" } });
  return (
    <BrowseShell
      title="Municipal"
      intro="Elected members of India's municipal bodies. Pick a corporation or browse them all, then filter by party or criminal record and sort by declared wealth or cases. Local bodies aren't covered by attendance records, so that field reads '—'; wealth, cases and party still apply."
      scope="municipal"
      {...data}
    />
  );
}
