"use client";

// Shared "Policy focus" primitives — the theme palette + the segmented bar + chips. Extracted from
// ProfileTabs so the profile tab AND the /compare page render the same policy-focus visuals with no
// duplication. Themes come from the ministry_theme map; colours are the categorical design tokens.

import type { ThemeFocus } from "@/lib/api";
import { themeColor } from "@/lib/themes";

// A single stacked bar of the theme mix. When `onSelect` is given, clicking a segment toggles the filter
// (synced with the chips); when omitted it's a static bar (usable directly from a server component, e.g.
// the /compare page — a function prop can't cross the server→client boundary).
export function SegmentedBar({ focus, selected = null, onSelect }: { focus: ThemeFocus[]; selected?: string | null; onSelect?: (t: string | null) => void }) {
  return (
    <div style={{ display: "flex", height: 16, borderRadius: 8, overflow: "hidden", background: "var(--rule)" }}>
      {focus.map((t) => {
        const active = selected === null || selected === t.theme;
        return (
          <button key={t.theme} title={`${t.theme} — ${Math.round(t.share * 100)}%`} aria-label={`${t.theme} ${Math.round(t.share * 100)} percent`}
            onClick={onSelect ? () => onSelect(selected === t.theme ? null : t.theme) : undefined}
            style={{ width: `${t.share * 100}%`, background: themeColor(t.theme), opacity: active ? 1 : 0.28,
              border: "none", borderRight: "1px solid var(--card)", cursor: onSelect ? "pointer" : "default", padding: 0, transition: "opacity .2s" }} />
        );
      })}
    </div>
  );
}

export function ThemeChip({ label, count, color, active, onClick }: { label: string; count: number; color?: string; active: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className="tap"
      style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12, padding: "4px 11px", borderRadius: 20, cursor: "pointer",
        border: `1px solid ${active ? "var(--accent)" : "var(--rule)"}`, background: active ? "var(--accent-soft)" : "var(--card)",
        color: active ? "var(--accent-soft-fg)" : "var(--ink2)" }}>
      {color && <span style={{ width: 8, height: 8, borderRadius: 8, background: color, display: "inline-block" }} />}
      {label} <span className="mono" style={{ color: active ? "var(--accent-soft-fg)" : "var(--muted)" }}>{count}</span>
    </button>
  );
}
