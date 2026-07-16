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

/** Compact US$ for macro figures: $3.96T / $700.1B / $2,740. (World Bank series are US$, not ₹.) */
export function usdCompact(n: number): string {
  const abs = Math.abs(n);
  if (abs >= 1e12) return `$${(n / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `$${(n / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
  return `$${Math.round(n).toLocaleString("en-US")}`;
}

/** Compact plain count: 1.46B / 146.4M / 25,300. */
export function countCompact(n: number): string {
  const abs = Math.abs(n);
  if (abs >= 1e9) return `${(n / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  return Math.round(n).toLocaleString("en-IN");
}

/** Trim trailing zeros from a fixed-decimal string ("98.00" -> "98", "24.80" -> "24.8"). */
function trimZeros(s: string): string {
  return s.includes(".") ? s.replace(/\.?0+$/, "") : s;
}

/** Compact count in Indian units: 24.8 crore / 14.72 lakh / 48,246. For counts an Indian reader reads by
 *  eye (schools, post offices, colleges) — the lakh/crore counterpart to countCompact's B/M. */
export function countIndian(n: number): string {
  const abs = Math.abs(n);
  if (abs >= 1e7) return `${trimZeros((n / 1e7).toFixed(2))} crore`;
  if (abs >= 1e5) return `${trimZeros((n / 1e5).toFixed(2))} lakh`;
  return Math.round(n).toLocaleString("en-IN");
}

/** Bare number at a sensible precision for its magnitude (97 / 72.2 / 1.96). */
export function smartNumber(n: number): string {
  const abs = Math.abs(n);
  if (abs >= 100) return Math.round(n).toLocaleString("en-IN");
  if (abs >= 10) return n.toFixed(1);
  return n.toFixed(2);
}

/** Render a macro-indicator value per its catalog `format` hint (see macro_indicator_def.format). */
export function indicatorValue(value: number, format: string): string {
  switch (format) {
    case "usd_compact":
      return usdCompact(value);
    case "pct":
      return `${smartNumber(value)}%`;
    case "count_compact":
      return countCompact(value);
    case "count_in":
      return countIndian(value);
    default:
      return smartNumber(value);
  }
}

/** Year-on-year change for a change chip: the last two points' delta as a signed %, with a good/bad tone
 *  keyed to polarity (+1 higher-is-better, -1 lower-is-better, 0 neutral). null when < 2 points. */
export function indicatorChange(
  points: { year: number; value: number }[],
  polarity: number,
): { text: string; tone: "good" | "bad" | "flat" } | null {
  if (points.length < 2) return null;
  const prev = points[points.length - 2].value;
  const curr = points[points.length - 1].value;
  if (prev === 0 || !isFinite(prev) || !isFinite(curr)) return null;
  const pct = ((curr - prev) / Math.abs(prev)) * 100;
  const sign = curr > prev ? 1 : curr < prev ? -1 : 0;
  const arrow = sign > 0 ? "▲" : sign < 0 ? "▼" : "→";
  const mag = Math.abs(pct);
  const text = `${arrow} ${mag < 1 ? mag.toFixed(2) : mag.toFixed(1)}%`;
  const tone = polarity === 0 || sign === 0 ? "flat" : sign === polarity ? "good" : "bad";
  return { text, tone };
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
