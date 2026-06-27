// Typed client for the FastAPI read layer. Called from server components only (no DB creds in browser).
// Run `npm run codegen` (with the API up) to generate src/types/api.ts from OpenAPI, then replace the
// hand-written shapes below with the generated ones.

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
  self_income: number | null;
  source: Source;
}

export interface CriminalCase {
  case_number: string | null;
  court: string | null;
  filed_year: number | null;
  status: string;
  is_convicted: boolean;
  severity: string | null;
  sections: string[];
  description: string | null;
  source: Source;
}

export interface PersonResume {
  id: number;
  display_name: string;
  office_terms: OfficeTerm[];
  party_history: PartyStint[];
  wealth: AffidavitWealth[];
  criminal_cases: CriminalCase[];
}

export async function getPersonResume(id: number): Promise<PersonResume | null> {
  const res = await fetch(`${API_BASE}/persons/${id}`, { next: { revalidate: 3600 } });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}
