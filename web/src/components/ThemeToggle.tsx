"use client";

import { useEffect, useState } from "react";

type Theme = "light" | "dark";

/**
 * Icon-only theme switch: one button showing a sun (light) or moon (dark); clicking toggles.
 * The visible icon is driven by html[data-theme] in CSS, so it is correct even before hydration.
 */
export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    const saved = (document.documentElement.getAttribute("data-theme") as Theme) || "light";
    setTheme(saved);
  }, []);

  function toggle() {
    const next: Theme = theme === "light" ? "dark" : "light";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    try {
      localStorage.setItem("nr-theme", next);
    } catch {
      /* ignore */
    }
  }

  const label = `Switch to ${theme === "light" ? "dark" : "light"} theme`;
  return (
    <button className="nr-theme-btn" aria-label={label} title={label} onClick={toggle}>
      <svg
        className="nr-theme-sun"
        aria-hidden
        viewBox="0 0 24 24"
        width="15"
        height="15"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      >
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2.8v2M12 19.2v2M2.8 12h2M19.2 12h2M5.5 5.5l1.4 1.4M17.1 17.1l1.4 1.4M18.5 5.5l-1.4 1.4M6.9 17.1l-1.4 1.4" />
      </svg>
      <svg className="nr-theme-moon" aria-hidden viewBox="0 0 24 24" width="15" height="15" fill="currentColor">
        <path d="M21 12.79A9 9 0 1 1 11.21 3a7 7 0 0 0 9.79 9.79Z" />
      </svg>
    </button>
  );
}
