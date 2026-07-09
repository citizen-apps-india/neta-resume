// Policy-theme palette (pure — safe to import in server or client components). The interactive
// SegmentedBar/ThemeChip live in components/resume/policy-focus.tsx and reuse themeColor from here.

export const THEME_COLORS: Record<string, string> = {
  "Economy & Industry": "var(--accent-2)",
  "Health": "var(--sev1)",
  "Education & Skills": "var(--sev2)",
  "Social Welfare & Justice": "var(--ok)",
  "Agriculture & Environment": "var(--accent-3)",
  "Infrastructure & Connectivity": "var(--accent)",
  "Governance & External": "var(--sev3)",
  "Other": "var(--muted)",
};

export function themeColor(theme: string | null | undefined): string {
  return THEME_COLORS[theme ?? "Other"] ?? "var(--muted)";
}
