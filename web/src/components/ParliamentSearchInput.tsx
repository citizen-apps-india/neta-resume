"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

/** Free-text input for /parliament/search. Routes to the same page with `q`, preserving the current
 *  kind/theme filters (which are plain URL links rendered server-side). Mirrors SearchBox's styling. */
export function ParliamentSearchInput({ initial = "", kind, theme }: { initial?: string; kind?: string; theme?: string }) {
  const router = useRouter();
  const [q, setQ] = useState(initial);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const v = q.trim();
    const p = new URLSearchParams();
    if (v.length >= 2) p.set("q", v);
    if (kind) p.set("kind", kind);
    if (theme) p.set("theme", theme);
    window.dispatchEvent(new Event("nr:nav")); // top progress bar for the programmatic push
    router.push(`/parliament/search${p.toString() ? `?${p.toString()}` : ""}`);
  }

  return (
    <form
      onSubmit={submit}
      className="focusring"
      style={{
        display: "flex", alignItems: "center", gap: 10, border: "1px solid var(--border)",
        borderRadius: 10, background: "var(--card2)", padding: "7px 7px 7px 16px", flex: 1, minWidth: 0,
      }}
    >
      <span style={{ color: "var(--faint)", fontSize: 16 }}>⌕</span>
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search questions & debates — e.g. railways, MSP, NEET…"
        aria-label="Search the parliamentary record"
        style={{
          border: "none", outline: "none", background: "transparent", fontFamily: "'Bricolage Grotesque',sans-serif",
          fontSize: 14.5, color: "var(--ink)", width: "100%",
        }}
      />
      <button
        type="submit"
        style={{
          flexShrink: 0, fontFamily: "'Bricolage Grotesque',sans-serif", fontSize: 13.5, fontWeight: 600,
          padding: "9px 18px", borderRadius: 7, border: "none", background: "var(--btn-bg)", color: "var(--btn-fg)", cursor: "pointer",
        }}
      >
        Search
      </button>
    </form>
  );
}
