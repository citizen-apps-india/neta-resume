// Typed client for the FastAPI read layer. Called from server components (no DB creds in browser).
// Run `npm run codegen` (with the API up) to regenerate src/types/api.ts from OpenAPI.

const API_BASE = process.env.NETA_API_BASE ?? "http://localhost:8000";

export interface Source {
  code: string;
  name: string;
  url: string | null;
  trust_tier: number;
}

export interface OfficeTerm {
  house: string;
  cycle_number: number;
  constituency: string | null;
  state: string | null;
  party: string | null;
  membership_type: string;
  start_date: string | null;
  end_date: string | null;
  status: string;
  source: Source;
}

export interface PartyStint {
  party: string;
  joined_date: string | null;
  left_date: string | null;
  is_current: boolean;
  join_reason: string | null;
  leave_reason: string | null;
  reason_source: Source | null;
  source: Source;
}

export interface AffidavitWealth {
  election_cycle: string;
  filed_year: number;
  total_assets: number;
  total_liabilities: number;
  movable_assets: number | null;
  immovable_assets: number | null;
  self_income: number | null;
  source: Source;
}

export interface CriminalCase {
  case_number: string | null;
  court: string | null;
  filed_year: number | null;
  status: string;
  is_convicted: boolean;
  severity: "heinous" | "serious" | "minor" | null;
  sections: string[];
  description: string | null;
  source: Source;
}

export interface PartySwitch {
  from_party: string | null;
  to_party: string;
  event_date: string | null;
  narrative: string | null;
  source: Source | null;
}

export interface PersonResume {
  id: number;
  display_name: string;
  native_name: string | null;
  photo_url: string | null;
  age: number | null;
  education: string | null;
  office_terms: OfficeTerm[];
  party_history: PartyStint[];
  party_switches: PartySwitch[];
  wealth: AffidavitWealth[];
  criminal_cases: CriminalCase[];
}

export interface PersonSummary {
  id: number;
  display_name: string;
  native_name: string | null;
  photo_url: string | null;
  current_party: string | null;
  current_house: string | null;
  constituency: string | null;
  net_assets: number | null;
  pending_cases: number;
  total_cases: number;
  top_severity: "heinous" | "serious" | "minor" | null;
}

async function getJSON<T>(path: string, revalidate = 3600): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { next: { revalidate } });
  if (!res.ok) throw new Error(`API ${res.status} for ${path}`);
  return res.json();
}

export async function getPersonResume(id: number): Promise<PersonResume | null> {
  const res = await fetch(`${API_BASE}/persons/${id}`, { next: { revalidate: 3600 } });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

export function listPersons(limit = 60, offset = 0, house?: string): Promise<PersonSummary[]> {
  const h = house ? `&house=${encodeURIComponent(house)}` : "";
  return getJSON<PersonSummary[]>(`/persons?limit=${limit}&offset=${offset}${h}`);
}

export function searchPersons(q: string): Promise<PersonSummary[]> {
  return getJSON<PersonSummary[]>(`/search?q=${encodeURIComponent(q)}`, 0);
}

/** Photos are served via the API proxy (upstream blocks cross-origin embedding). */
export function photoSrc(id: number, hasPhoto: string | null | undefined): string | null {
  return hasPhoto ? `${API_BASE}/persons/${id}/photo` : null;
}
