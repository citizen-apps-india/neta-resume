"use client";

import { useEffect, useState } from "react";

// CSS-variable palette the charts need. Recharts wants concrete colors, so we resolve these from
// getComputedStyle and re-resolve when the theme toggles (data-theme on <html>).
const VARS = [
  "--accent", "--accent-2", "--accent-3", "--sev1", "--sev2", "--sev3",
  "--faint", "--muted", "--ink2", "--rule2", "--card", "--ink", "--border",
] as const;
type Var = (typeof VARS)[number];
export type ThemeColors = Record<Var, string>;

function read(): ThemeColors {
  const out = {} as ThemeColors;
  const cs = typeof window !== "undefined" ? getComputedStyle(document.documentElement) : null;
  for (const v of VARS) out[v] = (cs?.getPropertyValue(v).trim() || "#888") as string;
  return out;
}

export function useThemeColors(): ThemeColors {
  const [colors, setColors] = useState<ThemeColors>(read);
  useEffect(() => {
    const obs = new MutationObserver(() => setColors(read()));
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => obs.disconnect();
  }, []);
  return colors;
}

/** Resolve a color string that may be a CSS var ("var(--sev1)") against the resolved palette. */
export function resolveColor(colors: ThemeColors, c: string): string {
  const m = c.match(/var\((--[a-z0-9-]+)\)/i);
  return m ? colors[m[1] as Var] ?? c : c;
}
