"use client";

import { useEffect, useState } from "react";

type Theme = "light" | "dark";

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    const saved = (document.documentElement.getAttribute("data-theme") as Theme) || "light";
    setTheme(saved);
  }, []);

  function apply(next: Theme) {
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    try {
      localStorage.setItem("nr-theme", next);
    } catch {
      /* ignore */
    }
  }

  return (
    <div style={{ display: "flex", border: "1px solid var(--border)", borderRadius: 9, overflow: "hidden", padding: 3, gap: 3, background: "var(--card)" }}>
      {(["light", "dark"] as Theme[]).map((t) => {
        const active = theme === t;
        return (
          <button
            key={t}
            className="seg"
            onClick={() => apply(t)}
            aria-pressed={active}
            style={{
              display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
              fontFamily: "'Bricolage Grotesque',sans-serif", fontSize: 12, fontWeight: 600, padding: "6px 12px",
              border: "none", borderRadius: 6, cursor: "pointer",
              background: active ? "var(--btn-bg)" : "transparent",
              color: active ? "var(--btn-fg)" : "var(--ink2)",
            }}
          >
            <span style={{ width: 9, height: 9, borderRadius: "50%", border: "1.5px solid currentColor", background: t === "dark" ? "currentColor" : "transparent" }} />
            {t === "light" ? "Light" : "Dark"}
          </button>
        );
      })}
    </div>
  );
}
