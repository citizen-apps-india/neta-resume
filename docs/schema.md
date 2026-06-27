# Database Schema

Source of truth: SQL in `db/migrations/`. ERD: `db/schema.dbml` (paste into dbdiagram.io).

**Design principle:** a fact table never stores a value without a provenance pointer. Every domain row
carries a `source_ref_id` and date-of-observation, so any datapoint links back to its source.

## Table map

| Table | Purpose | Key provenance |
|---|---|---|
| `house` | LS / RS / state-house registry (`jurisdiction`, `state_code`) | — |
| `term_cycle` | numbered house instance / election cycle (17th LS, …) | `eci_election_id` |
| `party` / `party_alias` | canonical party registry + spelling aliases | — |
| `source` | a data SOURCE system (sansad, myneta, tcpd, …) with `license`, `trust_tier` | — |
| `source_ref` | a native record identity in a source → `person_id` (NULL until resolved) | `native_url`, `raw_payload_ref` |
| `person` | **canonical person_id** (stable across houses/elections) | `tcpd_surf_id`, `wikidata_qid` |
| `person_name_variant` | every observed spelling (search + ER audit) | `source_id`, `script` |
| `office_term` | one posting in a legislature (the roster spine) | `source_ref_id` |
| `cabinet_post` | ministerial / leadership offices over time | `source_ref_id` |
| `party_affiliation` | affiliation w/ join/leave dates + reported narrative | `source_ref_id` |
| `party_switch_event` | explicit switch (from→to), reported narrative | `narrative_source_ref_id` |
| `affidavit` | ECI affidavit per election cycle (assets/liabilities/income) | `source_ref_id`, `raw_url` |
| `affidavit_line_item` | granular breakdown (cash, land, liability, income) | via affidavit |
| `criminal_case` | a case: status, `is_convicted`, derived `severity` | `source_ref_id`, `court_source_ref_id` |
| `case_charge` | IPC/BNS sections on a case (many per case) | via case |
| `legal_section` | IPC/BNS section catalog + crosswalk + `base_severity` | seed |

## Money

Store all amounts as **integer rupees** (`bigint`). The `₹ lakh/crore` text is parsed upstream in
`ingestion/neta_ingest/transform/money.py`. Never store a float; never store the raw string as the value.

## Year-over-year wealth

A query over `affidavit` rows for a person ordered by `filed_year`. No denormalized delta table in v1.

## State extensibility

`office_term` generalizes to states with zero schema change: add `house` rows (`jurisdiction='state'`,
`state_code`) + `term_cycle` rows. `constituency` / `rs_state_code` already cover the variants.

## Key constraints / indexes

- `source_ref(source_id, native_id)` UNIQUE — the dedup/idempotency key for ingestion upserts.
- `person.normalized_name` btree + `pg_trgm` GIN — fuzzy search + ER blocking.
- `affidavit(person_id, election_cycle, source_ref_id)` UNIQUE — re-runs upsert, never duplicate.
- Partial index `party_affiliation(person_id) WHERE is_current`.

## Provenance model

Two levels:
1. **Inline** `source_ref_id` on each fact table — the common, cheap case.
2. **`fact_source`** join table — used when one fact is corroborated by multiple sources (e.g. a party-switch
   confirmed by news + Wikidata).
