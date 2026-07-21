// Server-only geo helpers: resolve an approximate IP lat/long to a Lok Sabha constituency or a state
// assembly constituency, and map a Vercel region code to a state. Used by the homepage to feature the
// visitor's nearby MP + MLA.
//
// Boundaries (both imported, not in /public, so they're bundled server-side and never shipped to the
// browser), from the DataMeet India community (https://github.com/datameet/maps):
//   - Parliamentary Constituencies 2019 — CC BY 4.0        (pc-boundaries.json)
//   - Assembly Constituencies (India_AC)  — CC BY 2.5 India (ac-boundaries.json, simplified)
import pcData from "@/data/pc-boundaries.json";
import acData from "@/data/ac-boundaries.json";

type Ring = number[][];
type Polygon = Ring[];
interface GeoFeature {
  properties: Record<string, unknown>;
  geometry: { type: "Polygon" | "MultiPolygon"; coordinates: number[][][] | number[][][][] };
}

function pointInRing(x: number, y: number, ring: Ring): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0], yi = ring[i][1], xj = ring[j][0], yj = ring[j][1];
    if (((yi > y) !== (yj > y)) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

function pointInPolygon(x: number, y: number, poly: Polygon): boolean {
  if (!pointInRing(x, y, poly[0])) return false; // outer ring
  for (let k = 1; k < poly.length; k++) if (pointInRing(x, y, poly[k])) return false; // holes
  return true;
}

/** Build a bbox-accelerated (lat,lng) → value lookup over a GeoJSON feature set. A per-feature bounding
 *  box is precomputed once so far-away polygons are skipped before the expensive ring test. */
function makeLookup<T>(features: GeoFeature[], extract: (f: GeoFeature) => T): (lat: number, lng: number) => T | null {
  const bboxes: [number, number, number, number][] = features.map((f) => {
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    const polys = f.geometry.type === "MultiPolygon"
      ? (f.geometry.coordinates as number[][][][])
      : [f.geometry.coordinates as number[][][]];
    for (const poly of polys) for (const ring of poly) for (const [x, y] of ring) {
      if (x < minX) minX = x; if (x > maxX) maxX = x; if (y < minY) minY = y; if (y > maxY) maxY = y;
    }
    return [minX, minY, maxX, maxY];
  });
  return (lat: number, lng: number): T | null => {
    const x = lng, y = lat;
    for (let i = 0; i < features.length; i++) {
      const b = bboxes[i];
      if (x < b[0] || x > b[2] || y < b[1] || y > b[3]) continue;
      const g = features[i].geometry;
      const polys = g.type === "MultiPolygon"
        ? (g.coordinates as number[][][][])
        : [g.coordinates as number[][][]];
      for (const poly of polys) if (pointInPolygon(x, y, poly as Polygon)) return extract(features[i]);
    }
    return null;
  };
}

// DataMeet's assembly file uses a few legacy/variant state spellings; bridge them to our canonical state
// names so the MLA lookup matches. (Other names match after the API's case/punctuation normalization.)
const AC_STATE_ALIAS: Record<string, string> = {
  "ORISSA": "Odisha",
  "UTTARKHAND": "Uttarakhand",
  "JAMMU & KASHMIR": "Jammu and Kashmir",
};

const pcFeatures = (pcData as unknown as { features: GeoFeature[] }).features;
const acFeatures = (acData as unknown as { features: GeoFeature[] }).features;

const lookupPC = makeLookup(pcFeatures, (f) => f.properties.pc_name as string);
const lookupAC = makeLookup(acFeatures, (f) => {
  const raw = String(f.properties.st_name ?? "");
  return { ac: f.properties.ac_name as string, state: AC_STATE_ALIAS[raw.toUpperCase()] ?? raw };
});

/** Approximate (lat,lng) → Lok Sabha constituency name, or null if no polygon contains the point. */
export function pointToConstituency(lat: number, lng: number): string | null {
  return lookupPC(lat, lng);
}

/** Approximate (lat,lng) → state assembly constituency + (canonical) state, or null if none contains it. */
export function pointToAssembly(lat: number, lng: number): { ac: string; state: string } | null {
  return lookupAC(lat, lng);
}

// Vercel `x-vercel-ip-country-region` → state name (ISO 3166-2:IN subdivision codes). The API filter
// normalizes spelling/case, so these standard names match our stored state values.
export const REGION_TO_STATE: Record<string, string> = {
  AN: "Andaman and Nicobar Islands", AP: "Andhra Pradesh", AR: "Arunachal Pradesh", AS: "Assam",
  BR: "Bihar", CH: "Chandigarh", CT: "Chhattisgarh", DN: "Dadra and Nagar Haveli", DD: "Daman and Diu",
  DH: "Dadra and Nagar Haveli and Daman and Diu", DL: "Delhi", GA: "Goa", GJ: "Gujarat", HR: "Haryana",
  HP: "Himachal Pradesh", JK: "Jammu and Kashmir", JH: "Jharkhand", KA: "Karnataka", KL: "Kerala",
  LA: "Ladakh", LD: "Lakshadweep", MP: "Madhya Pradesh", MH: "Maharashtra", MN: "Manipur", ML: "Meghalaya",
  MZ: "Mizoram", NL: "Nagaland", OR: "Odisha", PY: "Puducherry", PB: "Punjab", RJ: "Rajasthan",
  SK: "Sikkim", TN: "Tamil Nadu", TG: "Telangana", TR: "Tripura", UP: "Uttar Pradesh", UT: "Uttarakhand",
  WB: "West Bengal",
};
