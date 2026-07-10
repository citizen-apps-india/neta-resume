import { redirect } from "next/navigation";

// The Parliament section is now a single tabbed console; this route redirects into the Trends tab,
// preserving the house so old links/bookmarks keep working.
export default async function TrendsRedirect({ searchParams }: { searchParams: Promise<{ house?: string }> }) {
  const sp = await searchParams;
  const p = new URLSearchParams({ tab: "trends" });
  if (sp.house === "rs") p.set("house", "rs");
  redirect(`/parliament?${p.toString()}`);
}
