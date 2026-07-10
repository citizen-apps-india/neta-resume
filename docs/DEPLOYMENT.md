# Deployment (current stack)

Near-$0/month footprint. Four layers, four services — the data layer is **independent of any laptop**:
schema + data reach the DB through GitHub Actions, not a local sync.

| Layer | Service | Notes |
|---|---|---|
| `web/` | **Vercel** | Next.js 15 SSR. Builds from the repo; `NETA_API_BASE` → the api. |
| `api/` | **Render** | FastAPI, read-only. `NETA_DATABASE_URL` = read role. |
| `db/`  | **Neon Postgres** (free tier) | Serverless; supports branches (use one as backfill staging). |
| `ingestion/` | **GitHub Actions** — `migrate.yml` (schema/seeds) + `ingest.yml` (pipelines) + `news.yml` | No extra compute; free runner minutes. |

> Note: earlier revisions of this doc described an AWS-hosted shape. The live stack is Vercel + Render +
> Neon + GitHub Actions, documented below.

## How data reaches the DB (independent of a laptop)

- **Schema/seeds** → `.github/workflows/migrate.yml` on merge to `main` (paths `db/**`) or manual dispatch:
  runs `neta migrate` (version-tracked in `schema_migrations`) + `neta seed`. Uses the **owner** DSN.
- **Data** → `.github/workflows/ingest.yml`: `workflow_dispatch` with free-form `args` runs any `neta`
  pipeline directly on Neon (idempotent), plus scheduled roster/attendance refreshes. Uses the **ingest**
  write-role DSN.
- `scripts/load_remote_db.sh` (full-replace) is **disaster-restore / first-bootstrap only**, not routine.

### One-time adoption on the existing Neon DB

The live DB already has the schema. Before the first `migrate.yml` run, baseline it once so the early
non-re-runnable ALTERs aren't replayed:

```bash
NETA_MIGRATE_DATABASE_URL="postgresql+psycopg://OWNER:PASS@HOST/neondb?sslmode=require" \
  uv run neta migrate --baseline    # records all current migrations as applied, executes nothing
```

(Ideally run against a Neon **branch** first to confirm, then the main DB.) After this, `migrate.yml`
applies only genuinely new migrations.

## How code reaches the running services (auto-deploy)

Merging to `main` advances the **DB** (via `migrate.yml`) but does **not** rebuild the running api/web by
itself — those are separate Render/Vercel builds. `.github/workflows/deploy.yml` closes that gap: on every
push to `main` (or manual dispatch) it pings each service's **deploy hook** so the merge actually goes live.

One-time setup (create the hooks, then add them as repo secrets):
- **Render** → the `api` service → **Settings → Deploy Hook** → copy the URL → repo secret `RENDER_DEPLOY_HOOK`.
- **Vercel** → the `web` project → **Settings → Git → Deploy Hooks** → create one targeting `main` → copy
  the URL → repo secret `VERCEL_DEPLOY_HOOK`.

A missing secret is skipped (the job logs a notice, doesn't fail). Trigger the first deploy by pushing to
`main` or **Actions → deploy → Run workflow**. (Turning OFF Render/Vercel's own git auto-deploy is optional —
this workflow is now the single source of truth; leaving both on just means a harmless double-build.)

## Environment variables / secrets

| Var | Where | Value |
|---|---|---|
| `NETA_MIGRATE_DATABASE_URL` | GitHub secret (migrate.yml) | Neon **owner** DSN (DDL) |
| `NETA_DATABASE_URL` | GitHub secret (ingest.yml/news.yml) | **ingest write-role** DSN |
| `RENDER_DEPLOY_HOOK` | GitHub secret (deploy.yml) | Render api service deploy-hook URL |
| `VERCEL_DEPLOY_HOOK` | GitHub secret (deploy.yml) | Vercel web project deploy-hook URL |
| `NETA_DATABASE_URL` | Render (api) | **read-only** role DSN |
| `NETA_API_BASE` | Vercel (web) | the api's public URL |
| `NETA_ALLOWED_ORIGINS` | Render (api) | the web origin(s), comma-separated |

DSN format (SQLAlchemy + psycopg): `postgresql+psycopg://USER:PASSWORD@HOST/neta?sslmode=require`. Store all
DSNs as secrets, never in the repo. **Rotate any credential that has ever been pasted into a chat/log.**

## Read-only / write DB roles

Create two least-privilege roles after the schema is loaded. `ingestion` writes; `api` only reads.

```sql
-- run as the Neon owner role, connected to the neta database

-- WRITE role (ingestion)
CREATE ROLE neta_ingest LOGIN PASSWORD '<strong-secret>';
GRANT CONNECT ON DATABASE neta TO neta_ingest;
GRANT USAGE ON SCHEMA public TO neta_ingest;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO neta_ingest;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO neta_ingest;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO neta_ingest;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO neta_ingest;

-- READ-ONLY role (api)
CREATE ROLE neta_read LOGIN PASSWORD '<strong-secret>';
GRANT CONNECT ON DATABASE neta TO neta_read;
GRANT USAGE ON SCHEMA public TO neta_read;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO neta_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO neta_read;
```

Point each service's `NETA_DATABASE_URL` at the matching role.

## One-time bootstrap (local → Neon)

Routine schema flows via `migrate.yml` and data via the `ingest` workflow (above). To seed a **brand-new
empty** Neon DB in one shot from a local copy, use `scripts/load_remote_db.sh` — **disaster-restore /
bootstrap only, not the routine path**:

```bash
TARGET_DSN="postgresql://neondb_owner:PASS@<neon-host>/neondb?sslmode=require" \
  ./scripts/load_remote_db.sh
```

Or bring the schema up with `neta migrate` + `neta seed`, then run the pipelines against Neon via the
`ingest` workflow's `workflow_dispatch`. See `docs/OPERATIONS.md`.

## Health checks

- **api:** `GET /health` → `{"status":"ok"}` — Render uses it as the health probe. OpenAPI at
  `/openapi.json`, docs at `/docs`.
- **db:** Neon dashboard status + a `SELECT 1`.
- **web:** the home page (`/`) renders once the api is reachable.

## Photo-cache caveat

The api proxies sansad.in member photos at `GET /persons/{id}/photo` and **disk-caches** them to
`api/.photo_cache/` (sansad sets `Cross-Origin-Resource-Policy: same-site`, so browsers can't embed them
directly; the api re-serves them with `Cross-Origin-Resource-Policy: cross-origin` and a 7-day
`Cache-Control`).

On **Render**, the container filesystem persists per running instance, so the cache warms naturally; the
7-day browser `Cache-Control` covers users across deploys/cold-starts. (If you ever move to a fully
ephemeral serverless host, front the photos with object storage for a durable shared cache.)
