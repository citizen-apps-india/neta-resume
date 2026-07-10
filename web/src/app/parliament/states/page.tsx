import { redirect } from "next/navigation";

// Redirects into the console's States tab, forwarding house + focus so profile deep-links
// ("See what {state} focuses on") still pin the right group.
export default async function StatesRedirect({ searchParams }: { searchParams: Promise<{ house?: string; focus?: string }> }) {
  const sp = await searchParams;
  const p = new URLSearchParams({ tab: "states" });
  if (sp.house === "rs") p.set("house", "rs");
  if (sp.focus) p.set("focus", sp.focus);
  redirect(`/parliament?${p.toString()}`);
}
