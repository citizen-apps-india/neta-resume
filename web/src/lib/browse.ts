import { getFacets, listPersons, type Facets, type PersonSummary } from "@/lib/api";

export const BROWSE_PAGE_SIZE = 60;

/** UI-level filter state, mirrored in the URL query. `house` is the LS/RS filter (directory scope);
 *  `state`/`corporation` are the scope-specific selectors (state-level / municipal). */
export type BrowseFilters = {
  q: string; party: string; house: string; state: string; corporation: string; cases: string; theme: string; sort: string;
};

export type BrowseData = {
  people: PersonSummary[]; total: number; facets: Facets; page: number; pageSize: number;
  filters: BrowseFilters; error: boolean;
};

type SP = Record<string, string | string[] | undefined>;
const one = (v: string | string[] | undefined): string => (Array.isArray(v) ? v[0] : v) ?? "";

const EMPTY_FACETS: Facets = { parties: [], states: [], houses: [], themes: [] };

/** Parse the browse URL params, fetch the matching page + total + facet options for a scope, and hand
 *  back everything the shell/browser render. Server-side (URL-driven pagination); ~60 rows per load. */
export async function loadBrowse(
  sp: SP,
  cfg: {
    base?: { house?: string; jurisdiction?: string };
    facetScope?: { house?: string; jurisdiction?: string };
  } = {},
): Promise<BrowseData> {
  const page = Math.max(1, Number(one(sp.page)) || 1);
  const filters: BrowseFilters = {
    q: one(sp.q), party: one(sp.party), house: one(sp.house), state: one(sp.state),
    corporation: one(sp.corporation), cases: one(sp.cases) || "any", theme: one(sp.theme),
    sort: one(sp.sort) || "assets",
  };
  try {
    const [res, facets] = await Promise.all([
      listPersons({
        limit: BROWSE_PAGE_SIZE,
        offset: (page - 1) * BROWSE_PAGE_SIZE,
        // house is fixed by scope (LS/RS pages) else the UI house filter (directory) or corporation (municipal)
        house: cfg.base?.house ?? (filters.house || filters.corporation || undefined),
        jurisdiction: cfg.base?.jurisdiction,
        state: filters.state || undefined,
        party: filters.party || undefined,
        cases: filters.cases !== "any" ? filters.cases : undefined,
        q: filters.q || undefined,
        theme: filters.theme || undefined,
        sort: filters.sort,
        revalidate: 0,
      }),
      getFacets(cfg.facetScope ?? cfg.base ?? {}),
    ]);
    return { people: res.items, total: res.total, facets, page, pageSize: BROWSE_PAGE_SIZE, filters, error: false };
  } catch {
    return { people: [], total: 0, facets: EMPTY_FACETS, page, pageSize: BROWSE_PAGE_SIZE, filters, error: true };
  }
}
