// Display helpers shared across the resume UI.

/** Integer rupees -> Indian short form (₹3.09 Cr / ₹29.02 L / ₹45,540). */
export function rupees(n: number | null | undefined): string {
  if (n == null) return "—";
  if (n >= 1_00_00_000) return `₹${(n / 1_00_00_000).toFixed(2)} Cr`;
  if (n >= 1_00_000) return `₹${(n / 1_00_000).toFixed(2)} L`;
  return `₹${n.toLocaleString("en-IN")}`;
}

export type Severity = "heinous" | "serious" | "minor" | null | undefined;

export interface SeverityMeta {
  label: string;
  fg: string; // css var
  bg: string;
  bd: string;
}

/** Map a derived severity to the design's sev1/sev2/sev3 tokens. */
export function severityMeta(sev: Severity): SeverityMeta {
  switch (sev) {
    case "heinous":
      return { label: "HEINOUS", fg: "var(--sev1)", bg: "var(--sev1-bg)", bd: "var(--sev1-bd)" };
    case "serious":
      return { label: "SERIOUS", fg: "var(--sev2)", bg: "var(--sev2-bg)", bd: "var(--sev2-bd)" };
    case "minor":
      return { label: "MINOR", fg: "var(--sev3)", bg: "var(--sev3-bg)", bd: "var(--sev3-bg)" };
    default:
      return { label: "UNCLASSIFIED", fg: "var(--muted)", bg: "var(--sunken)", bd: "var(--border2)" };
  }
}

/** The single colour used for a person's "cases" signal in lists. */
export function caseSignalColor(topSeverity: Severity, total: number): string {
  if (total === 0) return "var(--ok)";
  return severityMeta(topSeverity).fg;
}

/** Attendance % -> display string ("82%" / "—" when not on record). */
export function attendancePct(pct: number | null | undefined): string {
  return pct == null ? "—" : `${Math.round(pct)}%`;
}

/** Signal colour for an attendance %: good >=75, fair 50-75, poor <50, muted when absent. */
export function attendanceColor(pct: number | null | undefined): string {
  if (pct == null) return "var(--faint)";
  if (pct >= 75) return "var(--ok)";
  if (pct >= 50) return "var(--ink)";
  return "var(--sev2)";
}

/** Condense a verbose affidavit education string to its qualification level (the leading phrase MyNeta
 *  uses), e.g. "Post Graduate M.D. Internal Medicine…" -> "Post Graduate". Falls back to the first words. */
export function eduLevel(edu: string | null | undefined): string | null {
  if (!edu) return null;
  const s = edu.trim();
  const levels = [
    "Doctorate", "Post Graduate", "Graduate Professional", "Graduate",
    "12th Pass", "10th Pass", "8th Pass", "5th Pass",
    "Literate", "Illiterate", "Others",
  ];
  const hit = levels.find((l) => s.toLowerCase().startsWith(l.toLowerCase()));
  if (hit) return hit;
  return s.split(/[\s,]+/).slice(0, 2).join(" ");
}

export function year(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  return dateStr.slice(0, 4);
}

export function pretty(dateStr: string | null | undefined): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString("en-IN", { year: "numeric", month: "short" });
}
