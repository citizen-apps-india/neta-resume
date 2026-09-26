// The /eci-files/numbers tile grid + metric definitions (docs/eci-files/PHASE3-SPEC.md §3.1). Region
// slugs and tile positions are hand-written against the layout table in §1.1 — the backend's
// `data/eci_files/regions.json` is the source of truth, and this must be kept in step with it.
//
// docs/eci-files/PHASES-3-5-DECISIONS.md drops `appeals` as a tile *measure* ("A grid of 35 'no appeals
// figure' tiles invites the zero reading that 'missing ≠ zero' exists to prevent"): ECI_METRICS below has
// two entries, not the three in PHASE3-SPEC.md §3.1. Appeals still appears — as `EciStateMetrics.appeals_filed`
// on the region, shown by StateMetricTiles/AfterFinalFigures on the state page only.

import { countIndian } from "@/lib/format";
import type { EciRegionSummary, EciStateMetric } from "@/types/eci-files";

export type EciRegionSlug =
  | "jammu-and-kashmir" | "ladakh" | "chandigarh" | "punjab" | "himachal-pradesh" | "uttarakhand"
  | "arunachal-pradesh" | "rajasthan" | "haryana" | "delhi" | "uttar-pradesh" | "bihar" | "sikkim"
  | "assam" | "nagaland" | "gujarat" | "madhya-pradesh" | "chhattisgarh" | "jharkhand" | "west-bengal"
  | "meghalaya" | "manipur" | "dadra-and-nagar-haveli-and-daman-and-diu" | "maharashtra" | "telangana"
  | "odisha" | "tripura" | "mizoram" | "goa" | "karnataka" | "andhra-pradesh" | "lakshadweep" | "kerala"
  | "tamil-nadu" | "puducherry" | "andaman-and-nicobar-islands";

/** Row/col on the 9×7 tile grid (PHASE3-SPEC.md §1.1) — a `Record` over the slug union so `tsc` fails if
 *  a region is ever added to the backend's regions.json without a tile position landing here too. */
export const ECI_TILE_LAYOUT: Record<EciRegionSlug, { row: number; col: number }> = {
  "jammu-and-kashmir": { row: 0, col: 2 },
  ladakh: { row: 0, col: 3 },
  chandigarh: { row: 1, col: 1 },
  punjab: { row: 1, col: 2 },
  "himachal-pradesh": { row: 1, col: 3 },
  uttarakhand: { row: 1, col: 4 },
  "arunachal-pradesh": { row: 1, col: 8 },
  rajasthan: { row: 2, col: 1 },
  haryana: { row: 2, col: 2 },
  delhi: { row: 2, col: 3 },
  "uttar-pradesh": { row: 2, col: 4 },
  bihar: { row: 2, col: 5 },
  sikkim: { row: 2, col: 6 },
  assam: { row: 2, col: 7 },
  nagaland: { row: 2, col: 8 },
  gujarat: { row: 3, col: 1 },
  "madhya-pradesh": { row: 3, col: 2 },
  chhattisgarh: { row: 3, col: 3 },
  jharkhand: { row: 3, col: 4 },
  "west-bengal": { row: 3, col: 5 },
  meghalaya: { row: 3, col: 7 },
  manipur: { row: 3, col: 8 },
  "dadra-and-nagar-haveli-and-daman-and-diu": { row: 4, col: 1 },
  maharashtra: { row: 4, col: 2 },
  telangana: { row: 4, col: 3 },
  odisha: { row: 4, col: 4 },
  tripura: { row: 4, col: 7 },
  mizoram: { row: 4, col: 8 },
  goa: { row: 5, col: 1 },
  karnataka: { row: 5, col: 2 },
  "andhra-pradesh": { row: 5, col: 3 },
  lakshadweep: { row: 6, col: 0 },
  kerala: { row: 6, col: 2 },
  "tamil-nadu": { row: 6, col: 3 },
  puducherry: { row: 6, col: 4 },
  "andaman-and-nicobar-islands": { row: 6, col: 7 },
};

export const ECI_TILE_COLS = 9;
export const ECI_TILE_ROWS = 7;

export function isEciRegionSlug(s: string): s is EciRegionSlug {
  return Object.prototype.hasOwnProperty.call(ECI_TILE_LAYOUT, s);
}

/** Layout for a region whose slug isn't known to be one of the 36 (e.g. from an API response) — null
 *  rather than throwing, so a stray/renamed region drops its tile instead of crashing the grid. */
export function tileLayoutFor(slug: string): { row: number; col: number } | null {
  return isEciRegionSlug(slug) ? ECI_TILE_LAYOUT[slug] : null;
}

export type EciMetricId = "draft_left_off" | "net_change";
export type EciMetricParam = "left_off" | "net_change";

export interface EciMetricDef {
  id: EciMetricId;
  param: EciMetricParam;
  label: string;
  shortLabel: string;
  /** Title for the ranked bar list (docs/eci-files/designs/B-After-Numbers.dc.html): "Highest ..."/"Biggest ...". */
  rankTitle: string;
  /** 4 cut points -> 5 bands, lower-inclusive. */
  bins: number[];
  bandLabels: string[];
  encode: (m: EciStateMetric) => number;
  missingReason: (r: EciRegionSummary) => string;
  howWeCounted: string;
}

function hasStage(r: EciRegionSummary, stage: string): boolean {
  return r.stages.some((s) => s.stage === stage);
}

/** PHASE3-SPEC.md §3.1: the first of these that applies. */
function missingReason(r: EciRegionSummary, opts: { needsDraft: boolean; needsFinal: boolean }): string {
  if (r.exercise === "special_revision") return "Special Revision, not SIR";
  if (!r.has_figures) return "no figures yet";
  if (!hasStage(r, "before")) return "no pre-SIR figure";
  // launch fixdata S13: a Phase III state can have a published draft, or Lakshadweep/A&N a published
  // final, that just isn't in this record yet — "no draft figure"/"no final roll yet" read as if none
  // exists anywhere, which overstates the gap.
  if (opts.needsFinal && !hasStage(r, "final")) return "not in the record yet";
  if (opts.needsDraft && !hasStage(r, "draft")) return "not in the record yet";
  return "no appeals figure";
}

export const ECI_METRICS: EciMetricDef[] = [
  {
    id: "draft_left_off",
    param: "left_off",
    label: "Share of the pre-SIR roll not on the draft roll",
    shortLabel: "Left off the draft",
    rankTitle: "Highest share left off the draft",
    bins: [5, 10, 15, 20],
    bandLabels: ["under 5%", "5–10%", "10–15%", "15–20%", "20% or more"],
    encode: (m) => m.value,
    missingReason: (r) => missingReason(r, { needsDraft: true, needsFinal: false }),
    howWeCounted:
      "The pre-SIR roll minus the draft roll, divided by the pre-SIR roll. Both figures come from the " +
      "cited entries, and the dates differ by state. This counts names not carried into the draft. It is " +
      "not the number finally deleted: names can return through claims before the final roll, and new " +
      "electors are added.",
  },
  {
    id: "net_change",
    param: "net_change",
    label: "Net change from the pre-SIR roll to the final roll",
    shortLabel: "Net change to final",
    rankTitle: "Biggest net fall to the final roll",
    bins: [3, 6, 9, 12],
    bandLabels: ["under 3% fall, or a rise", "3–6% fall", "6–9% fall", "9–12% fall", "12% fall or more"],
    encode: (m) => -m.value,
    missingReason: (r) => missingReason(r, { needsDraft: false, needsFinal: true }),
    howWeCounted:
      "The final roll minus the pre-SIR roll, divided by the pre-SIR roll. A negative number means the " +
      "final roll is smaller. The colour shows the size of the fall; a rise would sit in the lightest " +
      "band. Where the source says so, final rolls exclude service voters.",
  },
];

export const ECI_METRIC_FOOTNOTE =
  "* rests on a computed or rounded figure. Andaman & Nicobar's draft, for example, is worked out from " +
  "the pre-SIR roll and a reported removal. The state page gives the method.";

export function eciMetricByParam(param?: string): EciMetricDef {
  return ECI_METRICS.find((m) => m.param === param) ?? ECI_METRICS[0];
}

/** The lowest band whose upper cut point is greater than `value`, band 5 otherwise. A negative `encode`
 *  (a rise, for `net_change`) is below every positive bin and so always lands in band 1. */
export function bandFor(metric: EciMetricDef, value: number): 1 | 2 | 3 | 4 | 5 {
  for (let i = 0; i < metric.bins.length; i++) {
    if (value < metric.bins[i]) return (i + 1) as 1 | 2 | 3 | 4 | 5;
  }
  return 5;
}

export type EciTileState =
  | { kind: "value"; band: 1 | 2 | 3 | 4 | 5; metric: EciMetricDef }
  | { kind: "no_measure"; reason: string }
  | { kind: "other_exercise" }
  | { kind: "no_figures"; phase: number | null };

export function tileState(region: EciRegionSummary, metric: EciMetricDef): EciTileState {
  if (region.exercise === "special_revision") return { kind: "other_exercise" };
  if (!region.has_figures) return { kind: "no_figures", phase: region.phase };
  const m = region.metrics[metric.id];
  if (!m) return { kind: "no_measure", reason: metric.missingReason(region) };
  return { kind: "value", band: bandFor(metric, metric.encode(m)), metric };
}

/** A tile's fully-resolved, plain-data view — everything `StateTileGrid` (a client component) needs to
 *  render and label one tile, with no function fields. `EciMetricDef.encode`/`missingReason` are ordinary
 *  functions, and a Server Component may not pass an object holding them as a prop into a "use client"
 *  component (React errors: "Functions cannot be passed directly to Client Components"), so every metric
 *  computation happens here, server-side, before the client boundary. */
export interface EciTileViewModel {
  slug: string;
  code: string;
  name: string;
  row: number;
  col: number;
  kind: EciTileState["kind"];
  band?: 1 | 2 | 3 | 4 | 5;
  valueText?: string;
  subText?: string;
  ariaLabel: string;
  readout: string;
}

/** Sentence-cases a metric label for mid-sentence use in a hover/screen-reader string, without
 *  lowercasing "SIR" into "sir" (N5). */
function lowerKeepingSIR(s: string): string {
  return s.toLowerCase().replace(/\bsir\b/g, "SIR");
}

function tileAriaLabel(region: EciRegionSummary, metric: EciMetricDef, state: EciTileState): string {
  if (state.kind === "value") {
    const m = region.metrics[metric.id]!;
    const base = `${region.name}: ${formatPercent(m.value, metric.id === "net_change")} — ${lowerKeepingSIR(metric.label)} ` +
      `(${countIndianApprox(m.count, false)} of ${countIndian(m.base)}). Phase ${romanPhase(region.phase)}. Open state page.`;
    return m.computed || m.approx ? `${base} Uses a computed or rounded figure.` : base;
  }
  if (state.kind === "no_measure") return `${region.name}: ${state.reason}. Open state page.`;
  if (state.kind === "other_exercise") return `${region.name}: Special Revision, a different exercise; not compared. Open state page.`;
  return `${region.name}: no figures yet. Open state page.`;
}

function tileReadout(region: EciRegionSummary, metric: EciMetricDef, state: EciTileState): string {
  if (state.kind === "value") {
    const m = region.metrics[metric.id]!;
    return `${region.name} · ${metricValueText(metric, m)} ${lowerKeepingSIR(metric.shortLabel)} · ${countIndianApprox(m.count, false)} of ${countIndian(m.base)}`;
  }
  if (state.kind === "no_measure") return `${region.name} · ${state.reason}`;
  if (state.kind === "other_exercise") return `${region.name} · Special Revision, not compared`;
  return `${region.name} · no figures yet`;
}

/** Regions -> tile view models, in DOM order (row, then col) — regions with no known tile position are
 *  dropped rather than crashing the grid. */
export function buildTileViewModels(regions: EciRegionSummary[], metric: EciMetricDef): EciTileViewModel[] {
  const out: EciTileViewModel[] = [];
  for (const region of regions) {
    const layout = tileLayoutFor(region.slug);
    if (!layout) continue;
    const state = tileState(region, metric);
    const model: EciTileViewModel = {
      slug: region.slug, code: region.code, name: region.name, row: layout.row, col: layout.col,
      kind: state.kind,
      ariaLabel: tileAriaLabel(region, metric, state),
      readout: tileReadout(region, metric, state),
    };
    if (state.kind === "value") {
      model.band = state.band;
      model.valueText = metricValueText(metric, region.metrics[metric.id]!);
    } else if (state.kind === "other_exercise") {
      model.valueText = "SR";
    } else if (state.kind === "no_measure") {
      model.valueText = "—";
      model.subText = state.reason;
    } else {
      model.subText = "no figures yet";
    }
    out.push(model);
  }
  return out.sort((a, b) => a.row - b.row || a.col - b.col);
}

const MINUS = "−";

/** "18.7%" / "−13.2%" (a real minus sign) for a signed value; unsigned for anything else. */
export function formatPercent(value: number, signed = false): string {
  if (!signed) return `${value.toFixed(1)}%`;
  const sign = value < 0 ? MINUS : "";
  return `${sign}${Math.abs(value).toFixed(1)}%`;
}

export function metricValueText(metric: EciMetricDef, m: EciStateMetric): string {
  const pct = formatPercent(m.value, metric.id === "net_change");
  // launch fixdata S4: a metric resting on a noted caveat (West Bengal's net_change, whose final
  // stage excludes the 60.07 lakh held under adjudication) gets the same "*" as an approx/computed one.
  return m.approx || m.computed || m.noted ? `${pct}*` : pct;
}

export function romanPhase(phase: number | null): string {
  return phase === 1 ? "I" : phase === 2 ? "II" : phase === 3 ? "III" : "—";
}

/** "1.46 crore" with a leading "≈" when the figure is approximate/rounded. Signed counts (net_change) are
 *  shown as a magnitude — the sign is already carried by the accompanying percent. */
export function countIndianApprox(count: number, approx: boolean): string {
  return `${approx ? "≈" : ""}${countIndian(Math.abs(count))}`;
}

/** Trim trailing zeros from a fixed-decimal string ("98.0" -> "98", "24.8" -> "24.8"). */
function trimZerosRough(s: string): string {
  return s.includes(".") ? s.replace(/\.?0+$/, "") : s;
}

/** launch fixdata B2: countIndian's own two-decimal precision ("74.43 lakh") reads as exact even when
 *  the underlying count is itself approximate or rounded — a computed before-minus-draft difference, for
 *  instance, built from two independently-rounded figures. For an approximate count, round to at most one
 *  decimal place instead and lead with "≈", so the display doesn't claim more precision than the record
 *  has. */
export function countIndianRough(count: number): string {
  const abs = Math.abs(count);
  if (abs >= 1e7) return `≈${trimZerosRough((abs / 1e7).toFixed(1))} crore`;
  if (abs >= 1e5) return `≈${trimZerosRough((abs / 1e5).toFixed(1))} lakh`;
  return `≈${Math.round(abs).toLocaleString("en-IN")}`;
}

