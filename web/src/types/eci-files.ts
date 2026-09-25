/**
 * Narrowed types for the ECI Files API (`api/neta_api/schemas.py`, generated as `components["schemas"]["Eci*"]`
 * in `src/types/api.ts`). The generated types leave every defaulted field optional and every enum a plain
 * string; these narrow them. Keep them in step with the generated file when the API changes.
 */

export type EciEntryKind = "event" | "person" | "rule" | "figure" | "case" | "statement";
export type EciEntryStatus = "documented" | "reported" | "claim" | "response";
export type EciDatePrecision = "day" | "month" | "year";
export type EciCheckStatus = "checked" | "unchecked";

export interface EciFigure {
  label: string;
  value: number;
  unit: string;
  as_of: string | null;
}

export interface EciEntryPerson {
  slug: string;
  name: string;
}

/** A stub reference to a response entry, embedded on the charge it answers. */
export interface EciResponseRef {
  id: string;
  title: string;
  date: string | null;
}

export interface EciCitation {
  position: number;
  url: string;
  publisher: string | null;
  title: string | null;
  published: string | null;
  tier: 1 | 2 | 3;
  archive_url: string | null;
  quote: string | null;
}

export interface EciEntry {
  id: string;
  area: string;
  kind: EciEntryKind;
  date: string | null;
  date_precision: EciDatePrecision;
  title: string;
  summary: string;
  status: EciEntryStatus;
  attributed_to: string | null;
  topics: string[];
  states: string[];
  figures: EciFigure[];
  details: Record<string, unknown>;
  notes: string | null;
  check_status: EciCheckStatus;
  people: EciEntryPerson[];
  response_to: string | null;
  responses: EciResponseRef[];
  citations: EciCitation[];
}

export interface EciTopicCount {
  topic: string;
  count: number;
}

export interface EciPersonCount {
  slug: string;
  name: string;
  count: number;
}

export interface EciTimelineCounts {
  checked: number;
  unchecked: number;
}

export interface EciTimeline {
  entries: EciEntry[];
  topics: EciTopicCount[];
  people: EciPersonCount[];
  counts: EciTimelineCounts;
}

export interface EciTenure {
  office?: string | null;
  from?: string | null;
  to?: string | null;
}

export interface EciCareerLine {
  from?: string | null;
  to?: string | null;
  post?: string | null;
  source_url?: string | null;
}

export interface EciPersonSummary {
  slug: string;
  name: string;
  role: string | null;
  tenure: EciTenure[];
  entry_count: number;
}

export interface EciPersonPage {
  person: { slug: string; name: string; profile: EciEntry | null };
  entries: EciEntry[];
}
