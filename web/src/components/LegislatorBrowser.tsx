"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { type PersonSummary, type Facets } from "@/lib/api";
import { type BrowseFilters } from "@/lib/browse";
import { DirectoryCard } from "@/components/DirectoryCard";

type Scope = "all" | "ls" | "rs" | "state" | "municipal" | "election";

/** "MAHARASHTRA" / "tamil nadu" → "Maharashtra" / "Tamil Nadu" for the state dropdown labels. */
const titleCase = (s: string) => s.toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());

const selectStyle: React.CSSProperties = {
  fontFamily: "'Bricolage Grotesque',sans-serif", fontSize: 13, color: "var(--ink)",
  background: "var(--card2)", border: "1px solid var(--border)", borderRadius: 8,
  padding: "9px 12px", cursor: "pointer", outline: "none",
};

/**
 * URL-driven browse engine: filter / sort / search / page all live in the query string, and the server
 * renders the matching ~60-row slice (so no giant client payload). Every control writes to the URL and
 * navigates; the loading bar + skeletons give feedback. Dropdown options come from `facets` (the client no
 * longer holds the full dataset). Used by the Lok Sabha, Rajya Sabha, Directory, State and Municipal pages.
 */
export function LegislatorBrowser({
  people,
  scope,
  facets,
  total,
  page,
  pageSize,
  filters,
}: {
  people: PersonSummary[];
  scope: Scope;
  facets: Facets;
  total: number;
  page: number;
  pageSize: number;
  filters: BrowseFilters;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  /** Apply query-param updates and navigate. Resets to page 1 unless `keepPage` (used by Prev/Next). */
  function navigate(updates: Record<string, string | null>, keepPage = false) {
    const params = new URLSearchParams(searchParams.toString());
    for (const [k, v] of Object.entries(updates)) {
      if (v === null || v === "") params.delete(k);
      else params.set(k, v);
    }
    if (!keepPage) params.delete("page");
    window.dispatchEvent(new Event("nr:nav"));
    const qs = params.toString();
    router.push(qs ? `${pathname}?${qs}` : pathname);
  }

  // Search: controlled locally, debounced into the URL so we don't navigate on every keystroke.
  const [q, setQ] = useState(filters.q);
  useEffect(() => setQ(filters.q), [filters.q]);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  function onSearch(v: string) {
    setQ(v);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => navigate({ q: v.trim() || null }), 350);
  }
  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);

  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: 14, overflow: "hidden", background: "var(--bg)", boxShadow: "0 24px 60px -32px var(--shadow)" }}>
      {/* prominent state selector — the primary control on the State Level page */}
      {scope === "state" && (
        <div style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: 12, padding: "18px clamp(14px,4vw,22px)", borderBottom: "1px solid var(--rule)", background: "var(--accent-soft)" }}>
          <label htmlFor="state-select" className="mono" style={{ fontSize: 11, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--accent-soft-fg)", fontWeight: 600 }}>
            State
          </label>
          <select
            id="state-select"
            aria-label="State"
            value={filters.state}
            onChange={(e) => navigate({ state: e.target.value || null })}
            style={{ ...selectStyle, fontSize: 16, fontWeight: 600, padding: "11px 16px", minWidth: 220, flex: "0 1 320px" }}
          >
            <option value="">All states</option>
            {facets.states.map((s) => (
              <option key={s.value} value={s.value}>{titleCase(s.value)} ({s.count})</option>
            ))}
          </select>
          <span style={{ fontSize: 12.5, color: "var(--accent-soft-fg)" }}>
            {facets.states.length === 1 ? "More states coming soon" : `${facets.states.length} states available`}
          </span>
        </div>
      )}

      {/* prominent corporation selector — the primary control on the Municipal page */}
      {scope === "municipal" && (
        <div style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: 12, padding: "18px clamp(14px,4vw,22px)", borderBottom: "1px solid var(--rule)", background: "var(--accent-soft)" }}>
          <label htmlFor="corp-select" className="mono" style={{ fontSize: 11, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--accent-soft-fg)", fontWeight: 600 }}>
            Corporation
          </label>
          <select
            id="corp-select"
            aria-label="Corporation"
            value={filters.corporation}
            onChange={(e) => navigate({ corporation: e.target.value || null })}
            style={{ ...selectStyle, fontSize: 16, fontWeight: 600, padding: "11px 16px", minWidth: 220, flex: "0 1 320px" }}
          >
            <option value="">All corporations</option>
            {facets.houses.map((c) => (
              <option key={c.value} value={c.value}>{c.value} ({c.count})</option>
            ))}
          </select>
          <span style={{ fontSize: 12.5, color: "var(--accent-soft-fg)" }}>
            {facets.houses.length === 1 ? "More corporations coming soon" : `${facets.houses.length} corporations available`}
          </span>
        </div>
      )}

      {/* controls */}
      <div style={{ padding: "16px clamp(14px,4vw,22px)", borderBottom: "1px solid var(--rule)", background: "var(--card)", display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
        <div className="focusring" style={{ display: "flex", alignItems: "center", gap: 8, flex: "1 1 240px", minWidth: 160, border: "1px solid var(--border)", borderRadius: 8, background: "var(--card2)", padding: "9px 12px" }}>
          <span style={{ color: "var(--faint)", fontSize: 14 }}>⌕</span>
          <input
            value={q}
            onChange={(e) => onSearch(e.target.value)}
            placeholder="Search name, party or constituency…"
            aria-label="Search this list"
            style={{ border: "none", outline: "none", background: "transparent", fontFamily: "'Bricolage Grotesque',sans-serif", fontSize: 13.5, color: "var(--ink)", width: "100%" }}
          />
        </div>

        {scope === "all" && (
          <select aria-label="House" value={filters.house} onChange={(e) => navigate({ house: e.target.value || null })} style={selectStyle}>
            <option value="">All houses</option>
            <option value="Lok Sabha">Lok Sabha</option>
            <option value="Rajya Sabha">Rajya Sabha</option>
          </select>
        )}

        <select aria-label="Party" value={filters.party} onChange={(e) => navigate({ party: e.target.value || null })} style={selectStyle}>
          <option value="">All parties</option>
          {facets.parties.map((p) => (
            <option key={p.value} value={p.value}>{p.value} ({p.count})</option>
          ))}
        </select>

        <select aria-label="Criminal cases" value={filters.cases} onChange={(e) => navigate({ cases: e.target.value === "any" ? null : e.target.value })} style={selectStyle}>
          <option value="any">Any cases</option>
          <option value="with">With cases</option>
          <option value="clean">No cases</option>
          <option value="heinous">Heinous</option>
          <option value="serious">Serious</option>
          <option value="minor">Minor</option>
        </select>

        {facets.themes.length > 0 && (
          <select aria-label="Policy area" value={filters.theme} onChange={(e) => navigate({ theme: e.target.value || null })} style={selectStyle}>
            <option value="">All policy areas</option>
            {facets.themes.map((t) => (
              <option key={t.value} value={t.value}>{t.value} ({t.count})</option>
            ))}
          </select>
        )}

        <select aria-label="Sort by" value={filters.sort} onChange={(e) => navigate({ sort: e.target.value === "assets" ? null : e.target.value })} style={selectStyle}>
          <option value="assets">Sort: Assets ↓</option>
          <option value="cases">Sort: Cases ↓</option>
          <option value="attendance">Sort: Attendance ↓</option>
          <option value="theme_questions">Sort: Questions ↓</option>
          <option value="name">Sort: Name A–Z</option>
        </select>
      </div>

      {/* count */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 22px", background: "var(--sunken)", borderBottom: "1px solid var(--rule)" }}>
        <span style={{ fontSize: 12.5, color: "var(--muted)" }}>
          <strong className="mono" style={{ color: "var(--ink)" }}>{total.toLocaleString("en-IN")}</strong>{" "}
          {total === 1 ? "legislator" : "legislators"}
        </span>
        {total > 0 && (
          <span className="mono" style={{ fontSize: 10.5, color: "var(--muted)" }}>
            SHOWING {from.toLocaleString("en-IN")}–{to.toLocaleString("en-IN")}
          </span>
        )}
      </div>

      {/* grid */}
      <div style={{ padding: "clamp(14px,4vw,22px)", background: "var(--bg)" }}>
        {people.length === 0 ? (
          <div style={{ padding: "48px 24px", textAlign: "center", color: "var(--muted)", fontSize: 14 }}>
            No legislators match these filters.
          </div>
        ) : (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(min(100%, 270px), 1fr))", gap: 16, alignItems: "stretch" }}>
              {people.map((p) => (
                <DirectoryCard key={p.id} p={p} />
              ))}
            </div>
            {totalPages > 1 && (
              <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 14, marginTop: 24 }}>
                <button
                  type="button"
                  className="btnGhost"
                  disabled={page <= 1}
                  onClick={() => navigate({ page: String(page - 1) }, true)}
                  style={{ fontFamily: "'Bricolage Grotesque',sans-serif", fontSize: 13, fontWeight: 600, padding: "9px 18px", borderRadius: 9, border: "1px solid var(--border)", background: "var(--card2)", color: "var(--ink)", cursor: "pointer" }}
                >
                  ← Prev
                </button>
                <span className="mono" style={{ fontSize: 12, color: "var(--muted)", whiteSpace: "nowrap" }}>
                  Page {page.toLocaleString("en-IN")} of {totalPages.toLocaleString("en-IN")}
                </span>
                <button
                  type="button"
                  className="btnGhost"
                  disabled={page >= totalPages}
                  onClick={() => navigate({ page: String(page + 1) }, true)}
                  style={{ fontFamily: "'Bricolage Grotesque',sans-serif", fontSize: 13, fontWeight: 600, padding: "9px 18px", borderRadius: 9, border: "1px solid var(--border)", background: "var(--card2)", color: "var(--ink)", cursor: "pointer" }}
                >
                  Next →
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
