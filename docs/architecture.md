# Architecture

## Components

```
                ┌──────────────────────────────────────────────────────────┐
                │  ingestion/  (Python 3.12 + uv)                           │
  sources ─────▶│  fetch → transform (normalize) → resolve (entity) → upsert│──┐
  (sansad,      │  idempotent, scheduled via GitHub Actions cron            │  │
   myneta,      └──────────────────────────────────────────────────────────┘  │
   courts,                                                                       ▼
   tcpd, …)                                                            ┌──────────────────┐
                                                                       │   Postgres 16    │
                                                                       │  facts + every   │
                                                                       │  fact's source   │
                                                                       └────────┬─────────┘
                ┌──────────────────────────────────────────────────────────┐   │
   browser  ◀───│  web/  (Next.js 15, React 19, TS strict)                  │   │
                │  server components → API; SourceBadge on every fact       │   │
                └───────────────────────────┬──────────────────────────────┘   │
                                            │ typed client (codegen from OpenAPI)│
                                ┌───────────▼──────────────────────────────────▼─┐
                                │  api/  (FastAPI, Python 3.12)                    │
                                │  read-only aggregate: /persons/{id} = full resume│
                                │  reuses ingestion transform/ models              │
                                └─────────────────────────────────────────────────┘
```

## Why a separate FastAPI service (not Next.js API routes → Postgres)

- **Language colocation with ingestion.** Money parsing, section→severity, name normalization, and the
  Pydantic "resume" models already live in Python. The API reuses them instead of reimplementing in TS.
- **One contract.** FastAPI emits OpenAPI; `web/` codegens TypeScript types from it. The frontend never
  hand-rolls DB shapes.
- **Resume = heavy aggregate read.** A person page joins person + terms + party history + N affidavit cycles
  + cases + sources. That belongs in a tuned service layer, not scattered across React server components.
- **Provenance discipline.** A single read layer guarantees every emitted fact carries its `source_ref`.

Next.js renders **server components** that call FastAPI server-side (fast, SEO-friendly, no DB creds in the
browser). Postgres credentials live only in `api/` and `ingestion/`.

## Data flow invariant

> **A fact is never stored without a pointer to where it came from.** Every domain row carries a
> `source_ref_id`; the UI renders a provenance link for every datapoint.

## Ingestion run order (dependency-correct)

1. Seeds/reference — houses, parties + aliases, `legal_section` catalog.
2. TCPD/SURF — seed canonical `person` + IDs.
3. Roster (sansad) — `office_term`, create `source_ref`s.
4. resolve_persons — link roster source_refs → persons.
5. Affidavits (MyNeta + ADR backfill) — `affidavit`, `affidavit_line_item`.
6. Criminal (MyNeta) — `criminal_case`, `case_charge`; run section→severity transform.
7. Court enrichment (bharat-courts/ecourts) — update live status by CNR.
8. party_switch — diff `office_term.party_id` across cycles → `party_affiliation` + `party_switch_event`.
9. OpenSanctions in_sansad — QA / PEP cross-validation.

## Idempotency

Every write is an upsert keyed on a natural key (`source_ref(source_id,native_id)`,
`affidavit(person_id,election_cycle,source_ref_id)`, …). Re-running a pipeline never duplicates. Raw fetched
HTML/PDF/JSON is content-hashed into `ingestion/data/raw_cache/` (gitignored) as a permanent provenance archive.

## Scheduling

GitHub Actions cron (one workflow per pipeline + `workflow_dispatch` for manual/backfill). No server to host;
free at this cadence for a private repo. Move to Prefect only if/when stateful retries + a run UI are needed.
