# Local Backend Setup

How the backend is run locally today. (The repo also ships `docker-compose.yml` for Postgres; this
machine uses a Homebrew Postgres instead — either works, the DSN is the same.)

## Quick start: full stack via Docker Compose

`docker compose up` now brings up the whole stack — the **db**, **api**, and **web** services — so you
can run everything without installing uv/Node locally:

```bash
docker compose up            # db + api + web
docker compose up -d db      # just Postgres (run api/web with uv/npm as below)
```

The compose services use the same defaults documented here: DB DSN
`postgresql+psycopg://neta:neta@localhost:5432/neta`, api on `:8000`, web on `:3000` with
`NETA_API_BASE` pointed at the api service. Apply migrations + seeds (next section) once the db is up.

> **Prod env-override:** the same images run against a hosted DB and origins by overriding env —
> `NETA_DATABASE_URL` (read-only role for api, write role for ingestion), `NETA_API_BASE` (web → api),
> and `NETA_ALLOWED_ORIGINS` (api CORS). See [`DEPLOYMENT.md`](./DEPLOYMENT.md) for the AWS mapping.

The native setup below is the historical local workflow and remains fully supported.

## 1. Postgres

```bash
brew install postgresql@16
brew services start postgresql@16

# one-time: create role + db matching the default DSN
createuser -s neta
psql -d postgres -c "ALTER ROLE neta WITH LOGIN PASSWORD 'neta'"
createdb -O neta neta
```

Default DSN (override with `NETA_DATABASE_URL`):
`postgresql+psycopg://neta:neta@localhost:5432/neta`

## 2. Schema + seeds

```bash
export PGPASSWORD=neta
for f in db/migrations/0*.sql; do psql -h localhost -U neta -d neta -v ON_ERROR_STOP=1 -f "$f"; done
for f in db/seeds/houses.sql db/seeds/sources.sql db/seeds/parties.sql \
         db/seeds/ipc_bns_sections.sql db/seeds/severity_rules.sql; do
  psql -h localhost -U neta -d neta -v ON_ERROR_STOP=1 -f "$f"
done
```

## 3. Ingestion (Python 3.12 + uv)

```bash
cd ingestion
uv sync
export NETA_DATABASE_URL="postgresql+psycopg://neta:neta@localhost:5432/neta"

uv run pytest                                   # parser + transform tests (no network)
uv run neta myneta --cycle LS2024 --limit 20    # ingest 20 LS2024 winners from MyNeta
uv run neta myneta --candidate 5083             # ingest one specific candidate
```

Pipelines are **idempotent** (keyed on each candidate's `source_ref`), so re-running never duplicates.
Raw fetched HTML is cached under `ingestion/data/raw_cache/` (gitignored) as a provenance archive.

## 4. API (FastAPI)

```bash
cd api
uv sync
export NETA_DATABASE_URL="postgresql+psycopg://neta:neta@localhost:5432/neta"
uv run uvicorn neta_api.main:app --reload      # http://localhost:8000/docs

curl localhost:8000/persons/1                  # full resume aggregate (provenance on every fact)
curl "localhost:8000/search?q=godam"           # trigram name search
```

## Current state (Phase 1 vertical slice — DONE)

- Postgres schema (18 tables) + reference seeds (houses, sources, parties, IPC/BNS severity catalog).
- Real MyNeta ingestion: winners list + candidate pages → person, office_term, party_affiliation,
  affidavit (assets/liabilities), criminal_case + case_charge with **derived severity**.
- Table-based criminal-case parser (robust to MyNeta's varied FIR/section formats), validated by tests.
- FastAPI `/persons/{id}` resume aggregate + `/search`, every fact carrying a `source` link.

## Known refinements (tracked, not blocking)

- Parenthetical sub-sections (e.g. "126(2)") emit a spurious section "2" — cosmetic, null section_id,
  no severity impact.
- Auto-created parties (e.g. "Nationalist Congress Party – Sharadchandra Pawar") should be reviewed/
  merged into canonical parties + aliases.
- sansad.in roster (official member IDs, RS) not yet wired — MyNeta currently supplies roster for the slice.
- Entity resolution (SURF) bypassed for the slice (1 MyNeta candidate = 1 person); needed before
  multi-cycle / multi-source merges.
