import { BrowseShell } from "@/components/BrowseShell";
import { listPersons, type PersonSummary } from "@/lib/api";

export const dynamic = "force-dynamic";
export const metadata = { title: "Rajya Sabha" };

export default async function RajyaSabhaPage() {
  let people: PersonSummary[] = [];
  let error = false;
  try {
    people = await listPersons(2000, 0, "Rajya Sabha");
  } catch {
    error = true;
  }
  return (
    <BrowseShell
      title="Rajya Sabha"
      intro="The sitting members of the upper house — the Council of States — each representing a state or union territory. Rajya Sabha members file no candidate affidavit, so wealth and case fields read ‘—’; attendance and party history still apply."
      people={people}
      scope="rs"
      error={error}
    />
  );
}
