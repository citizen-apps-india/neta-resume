"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

/** Free-text input for /parliament/search. Routes to /parliament/search with `q`, preserving the current
 *  kind/theme/house filters. `big` gives the prominent full-width treatment used on the console. */
export function ParliamentSearchInput({ initial = "", kind, theme, house, big = false }: { initial?: string; kind?: string; theme?: string; house?: string; big?: boolean }) {
  const router = useRouter();
  const [q, setQ] = useState(initial);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const v = q.trim();
    const p = new URLSearchParams();
    if (v.length >= 2) p.set("q", v);
    if (kind) p.set("kind", kind);
    if (theme) p.set("theme", theme);
    if (house) p.set("house", house);
    window.dispatchEvent(new Event("nr:nav")); // top progress bar for the programmatic push
    router.push(`/parliament/search${p.toString() ? `?${p.toString()}` : ""}`);
  }

  return (
    <form
      onSubmit={submit}
      className="focusring"
      style={{
        display: "flex", alignItems: "center", gap: 12, border: "1px solid var(--border)",
        borderRadius: big ? 13 : 10, background: "var(--card2)", width: "100%", minWidth: 0,
        padding: big ? "9px 9px 9px 20px" : "7px 7px 7px 16px",
        boxShadow: big ? "0 2px 10px -6px var(--shadow)" : "none",
      }}
    >
      <span style={{ color: "var(--faint)", fontSize: big ? 19 : 16 }}>⌕</span>
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder={big ? "Search questions & debates by topic — railways, MSP, NEET…" : "Search questions & debates — e.g. railways, MSP, NEET…"}
        aria-label="Search the parliamentary record"
        style={{
          border: "none", outline: "none", background: "transparent", fontFamily: "'Bricolage Grotesque',sans-serif",
          fontSize: big ? 16 : 14.5, color: "var(--ink)", width: "100%",
        }}
      />
      <button
        type="submit"
        className="btnDark"
        style={{
          flexShrink: 0, fontFamily: "'Bricolage Grotesque',sans-serif", fontSize: big ? 14 : 13.5, fontWeight: 600,
          padding: big ? "11px 22px" : "9px 18px", borderRadius: big ? 9 : 7, border: "none",
          background: "var(--btn-bg)", color: "var(--btn-fg)", cursor: "pointer",
        }}
      >
        Search
      </button>
    </form>
  );
}
