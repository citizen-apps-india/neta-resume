import { BrowseShell } from "@/components/BrowseShell";
import { loadBrowse } from "@/lib/browse";

export const dynamic = "force-dynamic";
export const metadata = { title: "Rajya Sabha", description: "Every sitting Rajya Sabha MP — party, state represented, attendance and full career, from the public record. Search and compare." };

export default async function RajyaSabhaPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const data = await loadBrowse(await searchParams, { base: { house: "Rajya Sabha" } });
  return (
    <BrowseShell
      title="Rajya Sabha"
      intro="The sitting members of the upper house — the Council of States — each representing a state or union territory. Rajya Sabha members file no candidate affidavit, so wealth and case fields read ‘—’; attendance and party history still apply."
      scope="rs"
      {...data}
    />
  );
}
