# Deployment (current stack)

Near-$0/month footprint. Four layers, four services — the data layer is **independent of any laptop**:
schema + data reach the DB through GitHub Actions, not a local sync.

| Layer | Service | Notes |
|---|---|---|
| `web/` | **Vercel** | Next.js 15 SSR. Builds from the repo; `NETA_API_BASE` → the api. |
| `api/` | **Render** | FastAPI, read-only. `NETA_DATABASE_URL` = read role. |
| `db/`  | **Neon Postgres** (free tier) | Serverless; supports branches (use one as backfill staging). |
| `ingestion/` | **GitHub Actions** — `migrate.yml` (schema/seeds) + `ingest.yml` (pipelines) + `news.yml` | No extra compute; free runner minutes. |

> Historical note: this doc previously described an AWS shape (Amplify/App Runner/RDS). The live stack is
> Vercel + Render + Neon; the AWS notes are not used.

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
  uv run neta migrate --baseline    # records 0001–0016 as applied, executes nothing
```

(Ideally run against a Neon **branch** first to confirm, then the main DB.) After this, `migrate.yml`
applies only genuinely new migrations.

## Environment variables / secrets

| Var | Where | Value |
|---|---|---|
| `NETA_MIGRATE_DATABASE_URL` | GitHub secret (migrate.yml) | Neon **owner** DSN (DDL) |
| `NETA_DATABASE_URL` | GitHub secret (ingest.yml/news.yml) | **ingest write-role** DSN |
| `NETA_DATABASE_URL` | Render (api) | **read-only** role DSN |
| `NETA_API_BASE` | Vercel (web) | the api's public URL |
| `NETA_ALLOWED_ORIGINS` | Render (api) | the web origin(s), comma-separated |

DSN format (SQLAlchemy + psycopg): `postgresql+psycopg://USER:PASSWORD@HOST/neta?sslmode=require`. Store all
DSNs as secrets, never in the repo. **Rotate any credential that has ever been pasted into a chat/log.**

## Read-only / write DB roles

Create two least-privilege roles after the schema is loaded. `ingestion` writes; `api` only reads.

```sql
-- run as the RDS master user, connected to the neta database

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

## One-time data load (local → RDS)

Ingestion can also run directly against RDS, but the fastest bootstrap is to dump the local DB and restore it:

```bash
# dump local (Homebrew/Docker) Postgres
pg_dump "postgresql://neta:neta@localhost:5432/neta" -Fc -f neta.dump

# restore into RDS (use the master user; create roles first if not present)
pg_restore --no-owner --role=neta_ingest \
  -d "postgresql://MASTER:PASS@<rds-host>:5432/neta?sslmode=require" neta.dump
```

Alternatively load schema first (`db/migrations/0*.sql` then `db/seeds/*.sql`) and run the pipelines
against RDS via the `ingest.yml` `workflow_dispatch`. See `docs/OPERATIONS.md`.

## Health checks

- **api:** `GET /health` → `{"status":"ok"}`. Use it as the App Runner / Lambda / load-balancer health
  probe. OpenAPI lives at `/openapi.json`, docs at `/docs`.
- **db:** RDS instance status + a `SELECT 1`.
- **web:** the home page (`/`) renders once the api is reachable.

## Photo-cache caveat (serverless)

The api proxies sansad.in member photos at `GET /persons/{id}/photo` and **disk-caches** them to
`api/.photo_cache/` (sansad sets `Cross-Origin-Resource-Policy: same-site`, so browsers can't embed them
directly; the api re-serves them with `Cross-Origin-Resource-Policy: cross-origin` and a 7-day
`Cache-Control`).

- On **App Runner** the container filesystem persists per running instance, so the cache warms naturally.
- On **Lambda** the disk is **ephemeral** (`/tmp`, lost between cold starts and not shared across
  instances) → each cold start re-fetches photos. Options: (a) accept a per-instance cache (cheap, fine at
  this scale, relies on the 7-day browser `Cache-Control`); or (b) front photos with **S3** (cache the
  bytes in a bucket / serve via CloudFront) for a durable shared cache. Prefer (a) for year one.
