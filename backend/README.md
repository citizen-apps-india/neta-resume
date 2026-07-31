# Private control backend

Async FastAPI service for ingestion administration. Its structure follows the Hunr backend:

- `neta_backend/main.py` owns application lifespan, async engine, and sessionmaker;
- `neta_backend/database/models/` contains declarative SQLAlchemy models;
- `database/migrations/` is the Alembic revision chain;
- `neta_backend/database/session.py` injects `AsyncSession` into future routers;
- `neta_backend/pipeline/service.py` owns validated transactions and audit events.

The public read API remains in `api/`. The backend serves an authenticated operator console at
`/admin` and its same-origin JSON API at `/admin/api`. The local-token mode exists only for local
review and is rejected when `NETA_BACKEND_ENVIRONMENT=production`; production deployment remains
private until the OIDC step is configured. Alembic revision `pipeline_execution_0002` adds the durable
`pipeline_run` record used to claim schedules and reconcile Dagster execution status.

## Local run

From the repository root:

```bash
export NETA_BACKEND_DATABASE_URL="postgresql+asyncpg://neta:neta@localhost:5432/neta"
export NETA_BACKEND_ADMIN_AUTH_MODE="local_token"
export NETA_BACKEND_ADMIN_TOKEN="replace-with-at-least-24-characters"
export NETA_BACKEND_ADMIN_SESSION_SECRET="replace-with-at-least-32-characters"
export NETA_BACKEND_ADMIN_ACTOR="local-operator"
export NETA_BACKEND_ADMIN_COOKIE_SECURE="false"
uv run alembic -c backend/database/alembic.ini upgrade head
cd backend
uv run fastapi dev neta_backend/main.py --port 8001
```

The operator console is at `http://localhost:8001/admin`, OpenAPI is at
`http://localhost:8001/docs`, and health is `GET /health`. Do not run Dagster if you want to review
control mutations without dispatching queued runs.

The legacy SQL schema ends at `db/migrations/0030_*`. On an empty database, run `uv run neta migrate`
before Alembic. Existing databases adopt the no-op `legacy_0030` revision automatically.

See `docs/ingestion/admin-console.md` for the authentication boundary, available actions, and local
review procedure.
