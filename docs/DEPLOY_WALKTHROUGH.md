# Deploy Neta-Resume — beginner walkthrough

A click-by-click guide to put the site live on the current stack. `docs/DEPLOYMENT.md` is the terse
reference; **this** is the hand-held version. No prior cloud experience assumed.

## The plan (and why)

Three pieces to host — the **database**, the **API**, and the **website** — plus **data loading**, which
runs itself on GitHub Actions (no server). All free-tier.

| Piece | Where | Why | Cost |
|------|-------|-----|------|
| **Database** | **Neon** (neon.tech) | Serverless Postgres, public SSL endpoint → the API reaches it with zero networking setup. Free tier, DB branching. | **$0** |
| **API** (FastAPI) | **Render** (render.com) | Deploys from GitHub, native Python 3.12 build, health checks. | Free (or ~$7/mo) |
| **Website** (Next.js) | **Vercel** (vercel.com) | Native Next.js, deploys from GitHub on every push. | **$0** |
| **Schema + data** | **GitHub Actions** | `migrate.yml` applies schema on merge; the `ingest` workflow runs pipelines directly on Neon. | **$0** |

```
 Browser ──▶ Vercel (web) ──▶ Render (api) ──▶ Neon (Postgres)
                                              ▲
                     GitHub Actions ──────────┘
              (migrate.yml = schema · ingest.yml = data)
```

---

## Stage 0 — Prerequisites (~5 min)

1. **GitHub**: the repo is already at `github.com/SahilSawant/neta-resume`, pushed. Good.
2. **uv + Postgres client** locally (only for the one-time DB bootstrap): `uv` (astral.sh/uv) and `psql`
   (`brew install libpq && brew link --force libpq`). Check `psql --version`.
3. A **local database with data** if you want to seed Neon from it (optional — you can also start empty).

---

## Stage 1 — Create the database (Neon) (~5 min)

1. **neon.tech** → sign up (GitHub login is fine) → **Create project** → name `neta-resume`, region closest
   to you, Postgres 16.
2. On the dashboard open **Connect** and copy the connection string. It looks like:
   ```
   postgresql://neondb_owner:XXXX@ep-cool-name-123456.<region>.aws.neon.tech/neondb?sslmode=require
   ```
3. **Save it privately** (password manager). Two forms you'll use:
   - **App form** (SQLAlchemy): prefix the scheme → `postgresql+psycopg://…` (used by the API + the
     GitHub secrets).
   - **Plain form**: as-is `postgresql://…` (used by `psql` / the bootstrap script).
   - Neon's default database is `neondb` — fine, the app doesn't care about the name.
   - (Optional hardening: create least-privilege `neta_read` (API) + `neta_ingest` (write) roles — see
     `docs/DEPLOYMENT.md`. Simplest start: use the `neondb_owner` DSN everywhere.)

---

## Stage 2 — Get the schema + data into Neon (~3 min)

**Path A — seed from your local DB (fastest if you have data):** from the repo root, using the **plain**
DSN:

```bash
TARGET_DSN="postgresql://neondb_owner:XXXX@ep-...neon.tech/neondb?sslmode=require" \
  ./scripts/load_remote_db.sh
```
This copies your local schema + all data into Neon and prints a row count. Then **adopt migrations** so
future schema changes are tracked (records the existing migrations without re-running them):
```bash
NETA_MIGRATE_DATABASE_URL="postgresql+psycopg://neondb_owner:XXXX@ep-...neon.tech/neondb?sslmode=require" \
  uv run neta migrate --baseline
```

**Path B — start empty:** build the schema with the migration runner, then load data later via the ingest
workflow (Stage 6):
```bash
NETA_MIGRATE_DATABASE_URL="postgresql+psycopg://neondb_owner:XXXX@ep-...neon.tech/neondb?sslmode=require" \
  uv run neta migrate      # applies db/migrations/*.sql
# same DSN:
  uv run neta seed         # reference seeds
```

---

## Stage 3 — Deploy the API (Render) (~8 min)

1. **render.com** → sign up (GitHub) → **New** → **Web Service** → connect the `neta-resume` repo.
2. Configure:
   - **Root Directory**: `api`
   - **Runtime**: Python 3 (3.12)
   - **Build Command**: `uv sync --frozen` (or `pip install -r requirements.txt` — both are in the repo)
   - **Start Command**: `uvicorn neta_api.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/health`
3. **Environment** → add:
   - `NETA_DATABASE_URL` = your Neon DSN **with** `postgresql+psycopg://…?sslmode=require` (read role if you
     made one, else `neondb_owner`).
   - `NETA_ALLOWED_ORIGINS` = `http://localhost:3000` (placeholder — fixed in Stage 5).
4. **Create Web Service**. When it's live, copy the URL (e.g. `https://neta-api-xxxx.onrender.com`).
5. Test: `<API URL>/health` → `{"status":"ok"}`; `<API URL>/persons?limit=3` → JSON.

---

## Stage 4 — Deploy the website (Vercel) (~5 min)

1. **vercel.com** → sign up (GitHub) → **Add New… → Project** → import `neta-resume`.
2. **Root Directory**: `web` (Vercel auto-detects Next.js).
3. **Environment Variables** → add `NETA_API_BASE` = your Render **API URL** (no trailing slash).
4. **Deploy**. Vercel gives a URL like `https://neta-resume.vercel.app` — your **website URL**.
5. Open it — pages render; photos/data may fail until CORS is set (next stage).

---

## Stage 5 — Connect the two (CORS) (~3 min)

The API only answers browsers from origins you allow.

1. **Render** → your API service → **Environment** → edit `NETA_ALLOWED_ORIGINS` = your **Vercel URL**
   (comma-separate several if needed, incl. any custom domain).
2. Save → Render redeploys (~2 min).
3. Reload the website — directory, photos, and profiles all work.

---

## Stage 6 — Turn on the independent data platform (~3 min)

Give GitHub Actions the two database DSNs so schema + data flow without your laptop.

1. **GitHub** → repo **Settings → Secrets and variables → Actions** → add:
   - `NETA_MIGRATE_DATABASE_URL` = Neon **owner** DSN (`+psycopg` form) — used by `migrate.yml`.
   - `NETA_DATABASE_URL` = ingest DSN (`+psycopg` form) — used by `ingest.yml` / `news.yml`.
   (Set these in the GitHub UI so the password never lands in a terminal history/chat.)
2. From now on:
   - **Schema** — add a `db/migrations/00NN_*.sql`, merge to `main` → `migrate.yml` applies just the new one.
   - **Data** — **Actions → ingest → Run workflow** → `args` = any command, e.g. `attendance --house rs`,
     `myneta --cycle LS2024 --limit 600`, `historical-lookup DL_MCD2012 --house dl_mcd --current-cycle DL_MCD2022`.
   - Scheduled roster/attendance/news refreshes run on their crons automatically.

`scripts/load_remote_db.sh` is now **restore-only** — you won't full-replace Neon in normal operation.

---

## Stage 7 — Verify end-to-end

- `<API URL>/health` → ok; `<API URL>/persons?limit=3` → JSON with `current_attendance_pct`.
- Website loads; directory shows photos + assets + attendance; a profile opens with all tabs.
- Push a trivial commit → Vercel rebuilds the web, Render redeploys the API automatically.
- Dispatch the `ingest` workflow once → it writes to Neon and the site reflects it on next load.

You're live. 🎉

---

## Appendix A — What it costs
- **Neon**: free tier. **Render**: free tier (spins down when idle; first request after idle is slow) or
  ~$7/mo to stay warm. **Vercel**: free tier. **GitHub Actions**: free. → effectively **$0**.

## Appendix B — Teardown
- Render → delete the API service. Vercel → delete the project. Neon → delete the project (or leave it, it's
  free). GitHub secrets → delete if you're done.

## Appendix C — Docker / local (optional)
The repo also ships `api/Dockerfile`, `web/Dockerfile`, and `docker-compose.yml` (handy for a local
Postgres via `docker compose up -d db`, or a container-based deploy). Not needed for this walkthrough.
