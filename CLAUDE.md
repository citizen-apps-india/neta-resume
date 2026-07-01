# CLAUDE.md — agent onboarding

A sourced public record of every Indian legislator. **No fact without a source.** This file is the
one-screen map for coding agents. Skim it, then dive into `docs/` for depth.

## Architecture (four layers, no cross-imports)

```
ingestion (Python 3.12 + uv)  ──writes──▶  Postgres 16  ──reads──▶  api (FastAPI)  ──HTTP──▶  web (Next.js 15 / React 19)
  scrapers + entity resolution             facts + every          read-only resume          server-rendered pages
  + severity + provenance                  fact's source_ref      aggregate + OpenAPI        provenance badge per fact
```

- **`db/`** — SQL migrations (`db/migrations/*.sql`, version-tracked via `neta migrate`) + reference seeds (`db/seeds/*.sql`). Source of truth for the schema; `db/schema.dbml` is a hand-kept ERD.
- **`ingestion/`** — Typer CLI (`neta`) of idempotent pipelines + the migration runner. **Writes** Postgres. Holds a write DB role. A uv workspace: `packages/neta-core` + `packages/neta-sources` + the `neta_ingest` runner.
- **`api/`** — FastAPI **read** layer. Assembles the resume aggregate, emits OpenAPI. Holds a read DB role. **Standalone** project (excluded from the workspace); reads pre-computed facts.
- **`web/`** — Next.js. Server components call `api` **over HTTP only** (no DB creds in the browser).

**Layering rules:** `web → api` over HTTP; `ingestion` writes, `api` reads; neither web nor api opens a
scraper. Postgres credentials live only in `ingestion/` and `api/`.

**DSN env:** `NETA_DATABASE_URL` (ingestion + api). **Web → api base:** `NETA_API_BASE`.

## Run each layer locally

Local dev DB is **Homebrew Postgres** historically (the repo also ships `docker-compose.yml` for the DB).
Default DSN: `postgresql+psycopg://neta:neta@localhost:5432/neta`. See `docs/local-dev.md`.

```bash
# DB — schema + seeds, version-tracked (schema_migrations). Same commands CI runs against Neon.
cd ingestion && uv sync && cd ..
export NETA_DATABASE_URL="postgresql+psycopg://neta:neta@localhost:5432/neta"
uv run neta migrate      # applies pending db/migrations/*.sql
uv run neta seed         # idempotent reference seeds (houses, sources, parties, …)

# ingestion
cd ingestion && uv sync
export NETA_DATABASE_URL="postgresql+psycopg://neta:neta@localhost:5432/neta"
uv run neta --help

# api  →  http://localhost:8000/docs  ·  GET /health
cd api && uv sync
export NETA_DATABASE_URL="postgresql+psycopg://neta:neta@localhost:5432/neta"
uv run uvicorn neta_api.main:app --reload

# web  →  http://localhost:3000   (NETA_API_BASE defaults to http://localhost:8000)
cd web && npm install && npm run dev
```

## The Typer CLI + pipeline run order

Every command is a thin wrapper over a pipeline in `ingestion/neta_ingest/pipelines/`. Pipelines are
**idempotent** (upsert on natural keys), so re-running is always safe. Command names (from `cli.py`):

| Command | Does |
|---|---|
| `neta migrate [--baseline]` | apply pending `db/migrations/*.sql` (tracked in `schema_migrations`); `--baseline` records-as-applied without running (one-time adoption). Uses owner DSN `NETA_MIGRATE_DATABASE_URL`. |
| `neta seed` | (re-)apply idempotent reference seeds |
| `neta myneta --cycle LS2024 --limit N` | MyNeta candidate page → person + affidavit + criminal_case (one pass). `--candidate ID` for one. |
| `neta affidavits` / `neta criminal` | aliases of `myneta` (MyNeta serves wealth + criminal on one page) |
| `neta roster --house ls --cycle 18` | sansad.in roster scaffold → office_term + source_ref |
| `neta ls-roster` | complete the LS roster + official photos from sansad.in (fill + add missing) |
| `neta rajya-sabha` | sitting RS roster from sansad.in (roster + photo; **no** affidavit data) |
| `neta enrich-missing` | backfill affidavits for LS seats MyNeta omitted (per-constituency) |
| `neta resolve` | entity-resolve unresolved `source_ref`s → canonical persons |
| `neta merge-cycles` | merge the same person across cycles (incumbents) + detect switches |
| `neta canon-parties` | merge abbr/full-name duplicate parties, clear false switches |
| `neta party-switch` | diff term parties → party_affiliation + party_switch_event (**scaffold: raises NotImplementedError**) |
| `neta enrich-switches` | attach sourced "why" narratives to detected switches |
| `neta native-names` | backfill Devanagari names from Wikidata (18th LS) |
| `neta attendance --house ls\|rs` | attach cumulative PRS attendance % to current-term office_terms |

**Typical full run order:** seeds → `ls-roster` / `rajya-sabha` → `myneta` (affidavits/criminal) →
`enrich-missing` → `resolve` / `merge-cycles` → `canon-parties` → `party-switch` → `enrich-switches` →
`native-names` → `attendance --house ls` then `--house rs`. Cross-cycle switch detection in practice
lives in `merge-cycles` today; `party-switch` is a stub. See `docs/OPERATIONS.md`.

## Provenance + idempotency rules (non-negotiable)

- **Every fact row carries a `source_ref_id`** (a `source_ref(source_id, native_id)` row) with a
  `raw_payload_ref` snapshot in `ingestion/data/raw_cache/` (content-addressed, gitignored).
- `provenance.record_source_ref(...)` upserts the source_ref; `provenance.cache_raw(...)` writes the
  content-hashed snapshot. Use these — don't hand-roll provenance.
- **trust_tier:** 1 = official (sansad/ECI/courts/data.gov.in), 2 = ADR/TCPD/PRS, 3 = reported/news/Wikidata.
- **Idempotency:** writes upsert on natural keys (`source_ref(source_id,native_id)`,
  `affidavit(person_id,election_cycle,source_ref_id)`, …). Several pipelines "delete this source_ref's
  derived facts, then re-insert" to stay idempotent. Re-running never duplicates.

## Testing / lint

```bash
uv run pytest                      # 30 tests (parsers + transforms + migrate runner, no network)
uv run ruff check packages ingestion
cd api       && uv run ruff check .
cd web       && npm run typecheck  # tsc --noEmit
```
CI (`.github/workflows/ci.yml`) runs all of the above per push/PR.

## Data-handling ethic (read before touching criminal/wealth)

- Criminal cases are **self-declared in ECI affidavits** and mostly **pending/unproven**. The product
  **asserts no guilt** — always show pending-vs-convicted and the source link; severity is *derived*,
  never adjudicated. See `docs/severity-rubric.md`, `docs/data-license.md`.
- Reported narratives (e.g. *why* someone switched parties) are labelled **reported** and carry a
  lower-trust (tier 3) source.
- **Missing ≠ zero.** RS members and rule-exempt LS members (ministers, PM, Speaker/Dep. Speaker, LoP)
  legitimately have no affidavit/attendance. Render `—`, **never 0**.
- MyNeta/ADR is **non-commercial use only, no bulk CSV** — keep the project non-commercial; scrape politely.

## Gotchas

- **Web fetch cache:** `web/src/lib/api.ts` calls the API with `next: { revalidate: 3600 }` (1-hour ISR).
  Data you just ingested won't appear instantly in the running web app.
- **Photo proxy (CORP):** sansad.in photos set `Cross-Origin-Resource-Policy: same-site`, so a browser
  refuses to embed them. The API proxies them at `GET /persons/{id}/photo`, fetching server-side and
  **disk-caching** to `api/.photo_cache/`. The web client builds that URL via `photoSrc()`. On serverless
  (Lambda) that disk cache is **ephemeral** — see `docs/DEPLOYMENT.md`.
- **mpsno namespacing:** sansad member id (`mpsno`) is namespaced per house into `source_ref.native_id`
  as `ls-{mpsno}` / `rs-{mpsno}` so LS and RS ids never collide.
- **CORS** is currently hard-coded to `http://localhost:3000` in `api/neta_api/main.py`; deployment makes
  it env-driven (`NETA_ALLOWED_ORIGINS`). See `docs/DEPLOYMENT.md`.
- **Money** is stored as **integer rupees** (`bigint`); `₹ lakh/crore` text is parsed upstream. Never store a float/string.

## Boundaries

Touch only the layer you're working in. Schema changes go through a new `db/migrations/00NN_*.sql` (+ keep
`db/schema.dbml` and `docs/DATA_DICTIONARY.md` in sync). The web client's TS types are codegen'd from the
API's OpenAPI (`npm run codegen` with the API up) — don't hand-edit generated shapes.
