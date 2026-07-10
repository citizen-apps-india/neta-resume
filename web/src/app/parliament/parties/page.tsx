import { redirect } from "next/navigation";

// Redirects into the console's Parties tab, forwarding house + focus so profile deep-links
// ("See what {party} MPs raise") still pin the right group.
export default async function PartiesRedirect({ searchParams }: { searchParams: Promise<{ house?: string; focus?: string }> }) {
  const sp = await searchParams;
  const p = new URLSearchParams({ tab: "parties" });
  if (sp.house === "rs") p.set("house", "rs");
  if (sp.focus) p.set("focus", sp.focus);
  redirect(`/parliament?${p.toString()}`);
}
