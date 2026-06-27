# Security posture — Neta-Resume

Neta-Resume serves **public** legislative data (it stores no user accounts, no PII beyond what is
already in public ECI/Parliament records). The threat model is therefore mostly about (a) not being a
vector to attack our own infrastructure, (b) not leaking the database, and (c) being a polite,
legally-defensible scraper. This document records the posture and the hardening applied.

## Architecture & trust boundaries

- **`ingestion/`** (Python CLI) — the only component with **write** access to Postgres. Run by an
  operator or GitHub Actions, never exposed to the internet.
- **`api/`** (FastAPI) — **read-only** HTTP surface. GET-only, no auth (the data is public), no write
  endpoints. Should run with a **read-only DB role** in production (see `docs/DEPLOYMENT.md`).
- **`web/`** (Next.js) — talks to the API over HTTP only; **never** touches the database and holds no
  secrets (only `NETA_API_BASE`, a public URL).
- **DB credentials** live only in `ingestion` and `api`, supplied via `NETA_DATABASE_URL`. No secrets
  are committed; `.env*` (except `.env.example`), `.photo_cache/`, and `ingestion/data/raw_cache/` are
  gitignored.

## Hardening applied (this pass)

1. **Photo-proxy SSRF/LFI guard** — `api/neta_api/routers/persons.py`. The `/persons/{id}/photo`
   endpoint fetches a URL read from the DB. It now requires `https://` and a host on an allowlist
   (`sansad.in`), rejecting `file://`, internal hosts, and other schemes (HTTP 400), and caps the
   download at 5 MB (Content-Length check + bounded read). This neutralises SSRF/LFI even if a bad
   `photo_url` ever reached the `person` table.
2. **Env-driven CORS** — `api/neta_api/deps.py` + `main.py`. Allowed browser origins come from
   `NETA_ALLOWED_ORIGINS` (comma-separated; default `http://localhost:3000`). Previously hardcoded to
   localhost, which both leaked dev assumptions and blocked deployment. Still GET-only, no credentials.

## Posture that was already sound (verified)

- **SQL injection:** all queries are parameterised (`text(...)` with bind params). The `{where}/{order}`
  fragments in `services/resume.py` are fixed server-controlled strings, not user input; the search `q`
  is bound, not interpolated. Pipeline table-name loops use hardcoded tuples.
- **Web XSS:** the only `dangerouslySetInnerHTML` is a static theme-init string (no dynamic data);
  fetch params are `encodeURIComponent`-escaped; `NETA_API_BASE` is server-side only.
- **Scraping posture:** `ingestion/neta_ingest/http/client.py` throttles (≥1 req/host/sec), backs off on
  429/5xx, and sends an identifying non-commercial User-Agent. Source licenses/ToS are tracked in
  `docs/data-license.md` and `NOTICE`.
- **Dependencies:** pinned via `uv.lock` (Python) and `package-lock.json` (Node); current major versions.

## Deployment requirements (see `docs/DEPLOYMENT.md`)

- Set `NETA_DATABASE_URL` and `NETA_ALLOWED_ORIGINS` via environment/secrets — never rely on the dev
  defaults in production.
- Give the API a **read-only** Postgres role; reserve a write role for ingestion.
- Terminate TLS at the edge (Amplify/App Runner handle this).

## Known follow-ups (out of scope for this pass)

- **API rate limiting** (per-IP) to blunt scraping/DoS of our own endpoints.
- **API versioning (`/v1`)** and **runtime response validation** on the web client (zod) to harden the
  FE/BE contract against drift.
- The photo proxy follows HTTP redirects within `urllib` defaults; the host allowlist covers the
  initial URL only. Photos are direct sansad file URLs (no redirects expected), but a redirect-aware
  re-validation would close the residual gap.

## Reporting

This is a public-interest hobby project. Report suspected issues to the repo owner
(sahil@magicweave.xyz) rather than filing a public issue with exploit detail.
