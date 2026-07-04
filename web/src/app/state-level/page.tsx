import { BrowseShell } from "@/components/BrowseShell";
import { loadBrowse } from "@/lib/browse";

export const dynamic = "force-dynamic";
export const metadata = { title: "State Level", description: "Members of India’s state legislative assemblies (MLAs) — declared assets, criminal cases and party history, sourced and comparable, state by state." };

export default async function StateLevelPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const data = await loadBrowse(await searchParams, { base: { jurisdiction: "state" } });
  return (
    <BrowseShell
      title="State Level"
      intro="Members of India's state legislative assemblies. Pick a state or browse them all, then filter by party or criminal record and sort by declared wealth or cases. State legislatures aren't covered by parliamentary attendance records, so that field reads '—'; wealth, cases and party still apply."
      scope="state"
      {...data}
    />
  );
}
