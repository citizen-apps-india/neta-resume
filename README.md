# Neta-Resume

A structured "resume" for every Indian legislator — built from **public records**, with a
**source link on every fact**.

Each politician page shows:

- **Office history** — every posting in a legislature over time (LS/RS now, state assemblies later)
- **Party history** — affiliations with when/why they joined and when/why they left (switches auto-detected; the "why" is *reported* narrative, clearly labelled)
- **Wealth** — assets, liabilities and income from ECI self-sworn affidavits, year-over-year
- **Criminal cases** — counts, IPC/BNS sections, a derived severity level, and pending-vs-convicted status

> This is a **non-commercial / hobby** project. Several upstream sources (notably MyNeta/ADR) are
> licensed for non-commercial use only. See [`NOTICE`](./NOTICE) and [`docs/data-license.md`](./docs/data-license.md).

## Architecture

```
ingestion (Python 3.12 + uv)  ──>  Postgres  ──>  api (FastAPI)  ──>  web (Next.js 15 / React 19)
   scrapers + entity resolution      facts +        read aggregate       server-rendered
   + severity + provenance           provenance      "resume" contract    resume pages
```

- **`ingestion/`** — scheduled Python pipelines that fetch updatable data from each source, normalize it, resolve entities to a canonical person, and upsert into Postgres. Pipelines are idempotent.
- **`api/`** — FastAPI read layer. Assembles the resume aggregate and emits an OpenAPI contract the frontend codegens its types from. Holds the only DB credentials besides ingestion.
- **`web/`** — Next.js app. Server components call the API; every fact renders a provenance badge.
- **`db/`** — SQL migrations + reference seeds (houses, parties, IPC/BNS section catalog, severity rules).
- **`docs/`** — data-source matrix, schema, severity rubric, entity-resolution design, data-license.

## Data sources (verified)

See **[`docs/data-sources.md`](./docs/data-sources.md)** for the full per-source index (URL, access
method, fields, licensing, reuse libraries). Spine: `sansad.in` roster · MyNeta/ADR affidavits ·
`bharat-courts`/eCourts for live case status · TCPD **SURF** for entity resolution · `data.gov.in` catalog.

## Status / build phases

- **Phase 0** — scaffold (this commit): repo skeleton, schema migrations, docs.
- **Phase 1** — end-to-end vertical slice for **one MP** (roster + affidavit + 1 case + party history rendered on a page, all with provenance).
- **Phase 2** — breadth on Lok Sabha (18th) with entity resolution at scale.
- **Phase 3** — add Rajya Sabha + historical backfill (YoY wealth).
- **Phase 4** — court live-status enrichment, party-switch narrative, search.
- **Phase 5** — validate state-assembly extension (zero schema change).

## Quickstart (dev)

```bash
# 1. Postgres
docker compose up -d db

# 2. Apply migrations + seeds
psql "$DATABASE_URL" -f db/migrations/0001_core_person.sql   # ... through 0007
psql "$DATABASE_URL" -f db/seeds/houses.sql                  # ... etc

# 3. Ingestion (Python)
cd ingestion && uv sync && uv run neta --help

# 4. API
cd api && uv sync && uv run uvicorn neta_api.main:app --reload

# 5. Web
cd web && npm install && npm run dev
```

See [`docs/architecture.md`](./docs/architecture.md) for the full picture.
