# Deployment (AWS, economical shape)

Target: a near-$0/month year-one footprint on AWS managed services. Four layers map to four services.

| Layer | Service | Notes |
|---|---|---|
| `web/` | **AWS Amplify Hosting** | Next.js 15 SSR. Builds from the repo; env-driven API base. |
| `api/` | **App Runner** (or **Lambda** behind API Gateway / Lambda Web Adapter) | FastAPI. Small, read-only. |
| `db/`  | **RDS Postgres `db.t4g.micro`** | Free tier 12 months, then ~$12–15/mo. |
| `ingestion/` | **GitHub Actions cron** (`.github/workflows/ingest.yml`) | No extra AWS compute. |

Read-only DB role for `api`; write role for `ingestion`. Estimated **~$0/mo for year 1** (RDS free tier;
Amplify/App Runner low-traffic free allowances; ingestion runs on GitHub-hosted runners).

## Environment variables per service

| Var | ingestion (GH Actions) | api (App Runner/Lambda) | web (Amplify) |
|---|---|---|---|
| `NETA_DATABASE_URL` | **write** role DSN (secret) | **read-only** role DSN (secret) | — |
| `NETA_API_BASE` | — | — | public/internal URL of the api service |
| `NETA_ALLOWED_ORIGINS` | — | the web origin(s), comma-separated | — |

DSN format (SQLAlchemy + psycopg): `postgresql+psycopg://USER:PASSWORD@HOST:5432/neta`. RDS gives the host;
require TLS in production (append `?sslmode=require`).

> **CORS will become env-driven.** Today `api/neta_api/main.py` hard-codes `allow_origins=["http://localhost:3000"]`.
> Before deploying, the api should read `NETA_ALLOWED_ORIGINS` (comma-separated) and pass it to the CORS
> middleware. Set it to the Amplify web origin (e.g. `https://main.xxxx.amplifyapp.com` and any custom domain).
> *(api code is owned by another worker; this doc only specifies the contract.)*

## Secrets

- Store both DSNs as secrets, never in the repo.
  - **ingestion:** GitHub Actions secret `NETA_DATABASE_URL` (already referenced by `ingest.yml`).
  - **api:** App Runner secret / Lambda env (back it with AWS Secrets Manager or SSM Parameter Store).
- RDS master password → Secrets Manager. The app roles below are *not* the master user.

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
