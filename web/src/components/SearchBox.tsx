"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

/** Search field that routes to the directory with the query. Used on landing + directory. */
export function SearchBox({
  placeholder = "Search by name, constituency or party…",
  initial = "",
  big = false,
}: {
  placeholder?: string;
  initial?: string;
  big?: boolean;
}) {
  const router = useRouter();
  const [q, setQ] = useState(initial);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const v = q.trim();
    router.push(v.length >= 2 ? `/directory?q=${encodeURIComponent(v)}` : "/directory");
  }

  return (
    <form
      onSubmit={submit}
      className="focusring"
      style={{
        display: "flex", alignItems: "center", gap: 12, border: "1px solid var(--border)",
        borderRadius: 10, background: "var(--card2)", padding: big ? "13px 16px" : "11px 14px",
        flex: 1, minWidth: 0,
      }}
    >
      <span style={{ color: "var(--faint)", fontSize: big ? 16 : 14 }}>⌕</span>
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder={placeholder}
        style={{
          border: "none", outline: "none", background: "transparent", fontFamily: "'Bricolage Grotesque',sans-serif",
          fontSize: big ? 14.5 : 13.5, color: "var(--ink)", width: "100%",
        }}
      />
    </form>
  );
}
