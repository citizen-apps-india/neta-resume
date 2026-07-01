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

- **Phase 0** — scaffold: repo skeleton, schema migrations, docs. **Done.**
- **Phase 1** — end-to-end vertical slice for one MP (roster + affidavit + case + party history + provenance). **Done.**
- **Phase 2** — breadth on the 18th Lok Sabha: full roster + official photos from sansad.in, MyNeta affidavits/criminal at scale, cross-cycle merge. **Done.**
- **Phase 3** — Rajya Sabha roster (sansad.in), Devanagari native names, **PRS attendance %** (LS + RS). **Done.**
- **Phase 4** — court live-status enrichment + structured party-switch narrative + search. *In progress.*
- **Phase 5** — state + municipal extension (Maharashtra Vidhan Sabha, Delhi MCD; zero schema change) + independent data platform (migrations-as-code, GitHub-Actions ingestion). **Done.**

**Now shipping:** a teal-themed Next.js directory + per-legislator resume page (office history, party
history, YoY wealth, criminal cases with derived severity, attendance %), every fact carrying a
provenance link. **Deployed** on Vercel (web) · Render (API) · Neon (Postgres); GitHub Actions runs the
migrations and ingestion pipelines directly on Neon — see [`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md).

## Documentation

- [`CLAUDE.md`](./CLAUDE.md) — agent onboarding: architecture, local run, CLI + pipeline order, gotchas.
- [`docs/architecture.md`](./docs/architecture.md) — why the four layers; data-flow invariant.
- [`docs/DATA_DICTIONARY.md`](./docs/DATA_DICTIONARY.md) — per-table/column reference + enums.
- [`docs/schema.md`](./docs/schema.md) — schema overview, constraints, provenance model.
- [`docs/OPERATIONS.md`](./docs/OPERATIONS.md) — pipeline runbook, backfills, recovery, tracing a fact.
- [`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md) — AWS path, env vars, DB roles, photo-cache caveat.
- [`docs/local-dev.md`](./docs/local-dev.md) · [`docs/data-sources.md`](./docs/data-sources.md) ·
  [`docs/entity-resolution.md`](./docs/entity-resolution.md) ·
  [`docs/severity-rubric.md`](./docs/severity-rubric.md) · [`docs/data-license.md`](./docs/data-license.md)

## Quickstart (dev)

```bash
# 1. Postgres (Docker, or Homebrew — same DSN; see docs/local-dev.md)
docker compose up -d db
export NETA_DATABASE_URL="postgresql+psycopg://neta:neta@localhost:5432/neta"

# 2. Schema + seeds — version-tracked (the same commands CI runs against Neon)
cd ingestion && uv sync && cd ..
uv run neta migrate      # applies db/migrations/*.sql
uv run neta seed         # reference seeds (houses, sources, parties, …)

# 3. Ingestion (Python)
cd ingestion && uv sync && uv run neta --help

# 4. API
cd api && uv sync && uv run uvicorn neta_api.main:app --reload

# 5. Web
cd web && npm install && npm run dev
```

See [`docs/architecture.md`](./docs/architecture.md) and [`CLAUDE.md`](./CLAUDE.md) for the full picture.
