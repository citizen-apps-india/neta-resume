# Private ingestion console

The FastAPI backend serves a same-origin operator console at `/admin` and JSON controls under
`/admin/api`. It is a private control surface, separate from the public `api/` and `web/` services.
The console reads Git-owned source definitions from `ingestion/source_registry/` and sends every
mutation through `PipelineControlService`, so database guardrails, config revisions, run-request
idempotency, and audit events apply equally to the UI, API clients, and Dagster.

## Available controls

- inspect all source definitions, registration state, effective runtime, next schedule, latest run,
  and failure/quarantine state;
- inspect the global execution journal, including requests that have not yet been claimed and the
  pipeline runs created from them;
- pause, resume, enable, disable, and change frequency, concurrency, rate, or retry limits;
- reset accumulated operator overrides to the current Git defaults;
- request run-now, retry, replay, or backfill with a JSON parameter object and idempotency key;
- quarantine a source or release its quarantine;
- review recent pipeline runs and immutable runtime revisions.

Every mutation requires an operator reason. The authenticated actor and reason are stored in the
revision, run request, or audit event. A run request is durable but does not execute until the Dagster
control-plane sensor is running.

The journal deliberately shows both the request and execution records. This keeps an operator command
visible during the interval before Dagster accepts it and preserves the request-to-run transition for
post-incident review. Structured control-plane run history begins at this cutover; older direct CLI and
GitHub Actions executions cannot be reconstructed as pipeline runs.

## Local authentication

Local review uses one configured bearer token. A successful browser login exchanges that token for a
short-lived, HMAC-signed, HTTP-only session cookie. Unsafe cookie-authenticated requests also require a
double-submit CSRF cookie/header. API clients may send the configured token as `Authorization: Bearer`.

```bash
export NETA_BACKEND_ENVIRONMENT="development"
export NETA_BACKEND_ADMIN_AUTH_MODE="local_token"
export NETA_BACKEND_ADMIN_TOKEN="replace-with-at-least-24-characters"
export NETA_BACKEND_ADMIN_SESSION_SECRET="replace-with-at-least-32-characters"
export NETA_BACKEND_ADMIN_ACTOR="local-operator"
export NETA_BACKEND_ADMIN_COOKIE_SECURE="false"
```

`local_token` is deliberately rejected when `NETA_BACKEND_ENVIRONMENT=production` — it exists for local
review only.

## Production: `github_oidc`

Production uses `NETA_BACKEND_ADMIN_AUTH_MODE=github_oidc`, which plugs into the same `AdminPrincipal`
dependency the routes already depend on, so no route handler changes. The console is a Render service;
see `docs/DEPLOYMENT.md` for the build and start commands.

| Variable | Notes |
|---|---|
| `NETA_BACKEND_ADMIN_GITHUB_CLIENT_ID` | from the GitHub OAuth app |
| `NETA_BACKEND_ADMIN_GITHUB_CLIENT_SECRET` | secret |
| `NETA_BACKEND_ADMIN_GITHUB_REDIRECT_URI` | `https://<service>/admin/login/github/callback` — must match the OAuth app exactly; it is sent both in the authorize step and the token exchange |
| `NETA_BACKEND_ADMIN_GITHUB_ALLOWED_LOGINS` | comma-separated GitHub logins |
| `NETA_BACKEND_ADMIN_GITHUB_ALLOWED_ORG` | optional alternative to the login list; `..._ALLOWED_TEAM` narrows it further |
| `NETA_BACKEND_ADMIN_SESSION_SECRET` | secret, at least 32 characters |

At least one of `ALLOWED_LOGINS` or `ALLOWED_ORG` must be set, or configuration validation fails at
import — which means a failed deploy rather than a runtime error. The requested OAuth scope is
`read:user` with a login allowlist, or `read:org` when an org check is configured.

The static login allowlist is re-checked on **every** request, so removing a login revokes access
immediately. Org- or team-only sessions are trusted for the session TTL.

Setting `NETA_BACKEND_ADMIN_AUTH_MODE=disabled` returns 404 for every admin page and API route, which
remains the correct setting for any deployment that should not expose the console at all.

## Safe local review

Apply legacy and Alembic migrations, seed reference data, and register the manifests before opening the
console. To inspect control behavior without executing source jobs, leave the sources paused. Pause,
runtime, quarantine, and run-request mutations will be stored in the preview database, while queued
runs remain undispatched.
