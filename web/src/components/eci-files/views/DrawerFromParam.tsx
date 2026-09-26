import { EntryDrawer } from "@/components/eci-files/EntryDrawer";
import { EntryDetail } from "@/components/eci-files/EntryDetail";
import { getEciEntryDetail } from "@/lib/api";

/** The drawer's content for any `?entry=` page (PHASE5-SPEC §6.1): fetches the one full entry the drawer
 *  needs — never the whole record — and renders it inside the shared {@link EntryDrawer} shell. `basePath`
 *  is the page the drawer is opened on, so a "responses" / "charge" / "case" link inside it stays there
 *  instead of jumping to the lane timeline. A separate async component so it streams independently of the
 *  page body above it (REDESIGN-SPEC §"Loading"). */
export async function DrawerFromParam({
  id, basePath, preserve,
}: {
  id: string;
  basePath: string;
  preserve?: Record<string, string | undefined>;
}) {
  const full = await getEciEntryDetail(id).catch(() => null);
  if (!full) return null;
  return (
    <EntryDrawer>
      <EntryDetail entry={full} basePath={basePath} preserve={preserve} />
    </EntryDrawer>
  );
}
