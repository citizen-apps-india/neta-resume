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

`local_token` is deliberately rejected when `NETA_BACKEND_ENVIRONMENT=production`. The Kubernetes
deployment step must add OIDC at the `AdminPrincipal` dependency boundary before exposing the console.
Until then, production configuration keeps `NETA_BACKEND_ADMIN_AUTH_MODE=disabled`, which returns 404
for admin pages and API routes.

## Safe local review

Apply legacy and Alembic migrations, seed reference data, and register the manifests before opening the
console. To inspect control behavior without executing source jobs, leave Dagster stopped. Pause,
runtime, quarantine, and run-request mutations will be stored in the preview database, while queued
runs remain undispatched.
