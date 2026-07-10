import { redirect } from "next/navigation";

// Redirects into the console's Ministries tab (old route kept alive for links/bookmarks).
export default async function MinistriesRedirect({ searchParams }: { searchParams: Promise<{ house?: string }> }) {
  const sp = await searchParams;
  const p = new URLSearchParams({ tab: "ministries" });
  if (sp.house === "rs") p.set("house", "rs");
  redirect(`/parliament?${p.toString()}`);
}
