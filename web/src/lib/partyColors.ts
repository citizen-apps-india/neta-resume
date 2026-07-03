// Party -> colour for the hemicycle seat-map. Hybrid scheme: recognisable brand hues for the major
// parties, and a muted, *deterministic* palette for the long tail (same party -> same tone every render),
// so the chart reads like an election-night graphic without turning the minimal site into a rainbow.

/** Normalise a party name for matching: lowercase, punctuation -> spaces, collapse whitespace. */
function norm(s: string): string {
  return s.toLowerCase().replace(/[().,'"&/-]/g, " ").replace(/\s+/g, " ").trim();
}

// Major parties as [alias-substring, hex]. First matching alias wins, so more-specific aliases that could
// be confused (AIADMK contains "dravida munnetra kazhagam"; CPI(M) contains "communist party of india")
// are listed BEFORE the shorter one. Hues hand-tuned so no two majors collide.
const MAJORS: [string, string][] = [
  ["bharatiya janata", "#F47216"],            // BJP — saffron
  ["indian national congress", "#2E9BE0"],    // INC — sky blue
  ["anna dravida munnetra", "#0E7C43"],       // AIADMK — green (before DMK)
  ["dravida munnetra kazhagam", "#E4322B"],   // DMK — red
  ["all india trinamool", "#3FA34D"],         // AITC/TMC — green
  ["trinamool", "#3FA34D"],
  ["aam aadmi", "#1B3A8B"],                   // AAP — navy
  ["samajwadi", "#C0227A"],                   // SP — magenta
  ["rashtriya janata dal", "#1F8A70"],        // RJD — teal-green
  ["janata dal united", "#1C7ED6"],           // JD(U) — blue
  ["janata dal secular", "#2FB6A8"],          // JD(S) — aqua
  ["telugu desam", "#E0A400"],                // TDP — yellow
  ["yuvajana", "#1560BD"],                    // YSRCP — blue
  ["bharat rashtra", "#D4327E"],              // BRS — pink
  ["telangana rashtra", "#D4327E"],
  ["biju janata", "#0E9B8E"],                 // BJD — teal
  ["communist party of india marxist", "#C1121F"], // CPI(M) — deep red (before CPI)
  ["communist party of india", "#E23B3B"],    // CPI — red
  ["shiv sena", "#E0721C"],                   // Shiv Sena (both factions) — orange
  ["nationalist congress", "#12A0C4"],        // NCP (both factions) — cyan
  ["bahujan samaj", "#2B39A8"],               // BSP — blue
  ["jharkhand mukti", "#1F7A4D"],             // JMM — green
  ["shiromani akali", "#0B5AA2"],             // SAD — blue
  ["indian union muslim league", "#0E8F5A"],  // IUML — green
  ["rashtriya lok dal", "#5AA469"],           // RLD — green
  ["telugu", "#E0A400"],
];

// Muted, desaturated long-tail palette — legible in both light and dark, assigned by a stable name hash.
const MUTED = [
  "#8A8F98", "#9C8B7A", "#7E9AA6", "#A88A9E", "#8F9E86",
  "#A69B76", "#7C8AA0", "#A08686", "#88A099", "#93889E", "#6F8F86", "#A2937E",
];

function hash(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return Math.abs(h);
}

/** A colour for a party name. Independents / unaffiliated / unknown -> neutral grey. */
export function partyColor(party: string | null | undefined): string {
  if (!party) return "#9AA0A6";
  const n = norm(party);
  if (n.includes("independent")) return "#9AA0A6";
  for (const [alias, hex] of MAJORS) if (n.includes(alias)) return hex;
  return MUTED[hash(n) % MUTED.length];
}
