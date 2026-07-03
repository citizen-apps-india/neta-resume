"use client";

import { useEffect, useMemo, useState } from "react";
import { type PersonSummary } from "@/lib/api";
import { DirectoryCard } from "@/components/DirectoryCard";
import { LegislatorTable } from "@/components/LegislatorTable";
import { Hemicycle } from "@/components/Hemicycle";

type Scope = "all" | "ls" | "rs" | "state" | "municipal" | "election";
type Sort = "assets" | "cases" | "attendance" | "name";
type CaseFilter = "any" | "with" | "clean" | "heinous" | "serious" | "minor";
type ViewMode = "cards" | "table" | "hemicycle";

const PAGE = 60;

/** "MAHARASHTRA" / "tamil nadu" → "Maharashtra" / "Tamil Nadu" for the state dropdown labels. */
const titleCase = (s: string) => s.toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());

const selectStyle: React.CSSProperties = {
  fontFamily: "'Bricolage Grotesque',sans-serif", fontSize: 13, color: "var(--ink)",
  background: "var(--card2)", border: "1px solid var(--border)", borderRadius: 8,
  padding: "9px 12px", cursor: "pointer", outline: "none",
};

/**
 * Client-side directory engine: instant search + filter + sort over the full in-memory list for a scope.
 * The dataset (a few hundred per house) is small enough to filter in the browser — no per-keystroke API
 * calls. Used by the Lok Sabha, Rajya Sabha and Directory pages (each passes its own people + scope).
 */
export function LegislatorBrowser({
  people,
  scope,
  initialQuery = "",
  defaultState,
  defaultCorporation,
}: {
  people: PersonSummary[];
  scope: Scope;
  initialQuery?: string;
  defaultState?: string;
  defaultCorporation?: string;
}) {
  const [q, setQ] = useState(initialQuery);
  const [party, setParty] = useState("");
  const [house, setHouse] = useState(""); // only used when scope === "all"
  // State Level opens pre-filtered to one state (e.g. Maharashtra); other scopes ignore this.
  const [state, setState] = useState(scope === "state" ? (defaultState ?? "") : "");
  // Municipal opens pre-filtered to one corporation (keyed on current_house, e.g. "Delhi MCD").
  const [corporation, setCorporation] = useState(scope === "municipal" ? (defaultCorporation ?? "") : "");
  const [caseFilter, setCaseFilter] = useState<CaseFilter>("any");
  const [sort, setSort] = useState<Sort>("assets");
  const [visible, setVisible] = useState(PAGE);

  // View mode (cards | table | hemicycle) — only offered on the Lok Sabha / Rajya Sabha pages, where the
  // seat total is fixed. Remembered across visits via localStorage (mirrors ThemeToggle).
  const [view, setView] = useState<ViewMode>("cards");
  const isHouse = scope === "ls" || scope === "rs";
  const effView: ViewMode = isHouse ? view : "cards";
  useEffect(() => {
    if (!isHouse) return;
    try {
      const saved = localStorage.getItem("nr-view");
      if (saved === "cards" || saved === "table" || saved === "hemicycle") setView(saved);
    } catch { /* ignore */ }
  }, [isHouse]);
  function chooseView(v: ViewMode) {
    setView(v);
    try { localStorage.setItem("nr-view", v); } catch { /* ignore */ }
  }

  // Party options present in this dataset, with counts, most-common first.
  const parties = useMemo(() => {
    const counts = new Map<string, number>();
    for (const p of people) if (p.current_party) counts.set(p.current_party, (counts.get(p.current_party) ?? 0) + 1);
    return [...counts.entries()].sort((a, b) => b[1] - a[1]);
  }, [people]);

  // State options present in this dataset (for the State Level page), alphabetical.
  const states = useMemo(() => {
    const set = new Set<string>();
    for (const p of people) if (p.state) set.add(p.state);
    return [...set].sort();
  }, [people]);

  // Corporation options present in this dataset (for the Municipal page), keyed on current_house.
  const corporations = useMemo(() => {
    const set = new Set<string>();
    for (const p of people) if (p.current_house) set.add(p.current_house);
    return [...set].sort();
  }, [people]);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    let out = people.filter((p) => {
      if (scope === "all" && house && p.current_house !== house) return false;
      if (scope === "state" && state && p.state !== state) return false;
      if (scope === "municipal" && corporation && p.current_house !== corporation) return false;
      if (party && p.current_party !== party) return false;
      if (caseFilter === "with" && p.total_cases <= 0) return false;
      if (caseFilter === "clean" && p.total_cases > 0) return false;
      if ((caseFilter === "heinous" || caseFilter === "serious" || caseFilter === "minor") && p.top_severity !== caseFilter)
        return false;
      if (needle) {
        const hay = `${p.display_name} ${p.native_name ?? ""} ${p.current_party ?? ""} ${p.constituency ?? ""}`.toLowerCase();
        if (!hay.includes(needle)) return false;
      }
      return true;
    });
    out = [...out].sort((a, b) => {
      switch (sort) {
        case "cases": return (b.total_cases ?? 0) - (a.total_cases ?? 0);
        case "attendance": return (b.current_attendance_pct ?? -1) - (a.current_attendance_pct ?? -1);
        case "name": return a.display_name.localeCompare(b.display_name);
        default: return (b.net_assets ?? -1) - (a.net_assets ?? -1); // assets desc, nulls last
      }
    });
    return out;
  }, [people, scope, q, party, house, state, corporation, caseFilter, sort]);

  // Reset the visible window whenever the result set changes.
  const shown = filtered.slice(0, visible);
  function resetAnd(fn: () => void) { fn(); setVisible(PAGE); }

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
            value={state}
            onChange={(e) => resetAnd(() => setState(e.target.value))}
            style={{ ...selectStyle, fontSize: 16, fontWeight: 600, padding: "11px 16px", minWidth: 220, flex: "0 1 320px" }}
          >
            <option value="">All states</option>
            {states.map((s) => (
              <option key={s} value={s}>{titleCase(s)}</option>
            ))}
          </select>
          <span style={{ fontSize: 12.5, color: "var(--accent-soft-fg)" }}>
            {states.length === 1 ? "More states coming soon" : `${states.length} states available`}
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
            value={corporation}
            onChange={(e) => resetAnd(() => setCorporation(e.target.value))}
            style={{ ...selectStyle, fontSize: 16, fontWeight: 600, padding: "11px 16px", minWidth: 220, flex: "0 1 320px" }}
          >
            <option value="">All corporations</option>
            {corporations.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <span style={{ fontSize: 12.5, color: "var(--accent-soft-fg)" }}>
            {corporations.length === 1 ? "More corporations coming soon" : `${corporations.length} corporations available`}
          </span>
        </div>
      )}

      {/* controls */}
      <div style={{ padding: "16px clamp(14px,4vw,22px)", borderBottom: "1px solid var(--rule)", background: "var(--card)", display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
        <div className="focusring" style={{ display: "flex", alignItems: "center", gap: 8, flex: "1 1 240px", minWidth: 160, border: "1px solid var(--border)", borderRadius: 8, background: "var(--card2)", padding: "9px 12px" }}>
          <span style={{ color: "var(--faint)", fontSize: 14 }}>⌕</span>
          <input
            value={q}
            onChange={(e) => resetAnd(() => setQ(e.target.value))}
            placeholder="Search name, party or constituency…"
            aria-label="Search this list"
            style={{ border: "none", outline: "none", background: "transparent", fontFamily: "'Bricolage Grotesque',sans-serif", fontSize: 13.5, color: "var(--ink)", width: "100%" }}
          />
        </div>

        {scope === "all" && (
          <select aria-label="House" value={house} onChange={(e) => resetAnd(() => setHouse(e.target.value))} style={selectStyle}>
            <option value="">All houses</option>
            <option value="Lok Sabha">Lok Sabha</option>
            <option value="Rajya Sabha">Rajya Sabha</option>
          </select>
        )}

        <select aria-label="Party" value={party} onChange={(e) => resetAnd(() => setParty(e.target.value))} style={selectStyle}>
          <option value="">All parties</option>
          {parties.map(([name, n]) => (
            <option key={name} value={name}>{name} ({n})</option>
          ))}
        </select>

        <select aria-label="Criminal cases" value={caseFilter} onChange={(e) => resetAnd(() => setCaseFilter(e.target.value as CaseFilter))} style={selectStyle}>
          <option value="any">Any cases</option>
          <option value="with">With cases</option>
          <option value="clean">No cases</option>
          <option value="heinous">Heinous</option>
          <option value="serious">Serious</option>
          <option value="minor">Minor</option>
        </select>

        {effView !== "hemicycle" && (
          <select aria-label="Sort by" value={sort} onChange={(e) => setSort(e.target.value as Sort)} style={selectStyle}>
            <option value="assets">Sort: Assets ↓</option>
            <option value="cases">Sort: Cases ↓</option>
            <option value="attendance">Sort: Attendance ↓</option>
            <option value="name">Sort: Name A–Z</option>
          </select>
        )}

        {isHouse && (
          <div role="group" aria-label="View mode" style={{ display: "flex", marginLeft: "auto", border: "1px solid var(--border)", borderRadius: 9, overflow: "hidden", padding: 3, gap: 3, background: "var(--card)" }}>
            {(([["cards", "Cards"], ["table", "Table"], ["hemicycle", "Seats"]]) as [ViewMode, string][]).map(([v, label]) => {
              const active = effView === v;
              return (
                <button
                  key={v}
                  type="button"
                  onClick={() => chooseView(v)}
                  aria-pressed={active}
                  style={{
                    fontFamily: "'Bricolage Grotesque',sans-serif", fontSize: 12, fontWeight: 600, padding: "6px 13px",
                    border: "none", borderRadius: 6, cursor: "pointer",
                    background: active ? "var(--btn-bg)" : "transparent",
                    color: active ? "var(--btn-fg)" : "var(--ink2)",
                  }}
                >
                  {label}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* count */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 22px", background: "var(--sunken)", borderBottom: "1px solid var(--rule)" }}>
        <span style={{ fontSize: 12.5, color: "var(--muted)" }}>
          <strong className="mono" style={{ color: "var(--ink)" }}>{filtered.length.toLocaleString("en-IN")}</strong>{" "}
          {filtered.length === 1 ? "legislator" : "legislators"}
        </span>
        {effView !== "hemicycle" && shown.length < filtered.length && (
          <span className="mono" style={{ fontSize: 10.5, color: "var(--muted)" }}>SHOWING {shown.length}</span>
        )}
      </div>

      {/* results */}
      <div style={{ padding: "clamp(14px,4vw,22px)", background: "var(--bg)" }}>
        {effView === "hemicycle" ? (
          <Hemicycle members={people} activeIds={new Set(filtered.map((p) => p.id))} scope={scope as "ls" | "rs"} />
        ) : filtered.length === 0 ? (
          <div style={{ padding: "48px 24px", textAlign: "center", color: "var(--muted)", fontSize: 14 }}>
            No legislators match these filters.
          </div>
        ) : (
          <>
            {effView === "table" ? (
              <LegislatorTable rows={shown} scope={scope as "ls" | "rs"} sort={sort} onSort={setSort} />
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(min(100%, 270px), 1fr))", gap: 16, alignItems: "stretch" }}>
                {shown.map((p) => (
                  <DirectoryCard key={p.id} p={p} />
                ))}
              </div>
            )}
            {shown.length < filtered.length && (
              <div style={{ display: "flex", justifyContent: "center", marginTop: 24 }}>
                <button
                  type="button"
                  className="btnGhost"
                  onClick={() => setVisible((v) => v + PAGE)}
                  style={{ fontFamily: "'Bricolage Grotesque',sans-serif", fontSize: 13, fontWeight: 600, padding: "10px 22px", borderRadius: 9, border: "1px solid var(--border)", background: "var(--card2)", color: "var(--ink)", cursor: "pointer" }}
                >
                  Show more ({(filtered.length - shown.length).toLocaleString("en-IN")} more)
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
