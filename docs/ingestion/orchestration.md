# Dagster execution plane and dlt history

`orchestration/` is the portable execution layer for manifest-backed sources. It is implemented and
testable locally, but it does not replace the deployed GitHub Actions schedules until the Kubernetes
cutover has passed parity checks.

```text
Git source manifest ──register──▶ pipeline_source_state ◀──admin revisions
                                      │
                         30-second Dagster sensor
                                      │ atomic claim
                                      ▼
                               pipeline_run row
                                      │ stable run key
                                      ▼
Dagster source asset: extract raw artifacts → parse/normalize → canonical Postgres write
                                      │
                                      └──dlt merge──▶ ingestion_history.raw_envelopes
```

## Responsibilities

- `SourceComponent` loads every manifest with an `orchestration.runner`, imports the approved
  `neta_ingest` entrypoint, and builds one Dagster asset job per source.
- `PipelineControlService.claim_dispatches` serialises scheduler replicas with a PostgreSQL advisory
  lock, respects enabled/paused/quarantined state and source concurrency, and creates a durable run
  before advancing a schedule.
- Dagster retries the asset according to the runtime snapshot captured on that run. Existing canonical
  writes are idempotent, so a retry can safely replay completed records.
- Deterministic Pydantic contract or parameter validation failures terminate immediately. Operational
  failures retain the configured retry policy and exponential delay; retry attempts are audit events.
- Failure and cancellation sensors reconcile infrastructure-level Dagster outcomes that occur outside
  the Python asset body.
- dlt schema-normalises and merges `RawEnvelope` metadata by `envelope_id` in its own
  `ingestion_history` schema. Response bodies remain in the rights-aware object store; a source with
  `store_raw: false` never has its body written by dlt.

The database role in `NETA_DATABASE_URL` must be allowed to create and maintain the dlt-owned
`ingestion_history` schema. The later deployment step will provision that grant explicitly; it is not
part of the public API's read-only role.

The dlt ledger is operational history, not a replacement for `source_ref` provenance on canonical facts.
Search/OpenSearch projections and canonical-change history remain a later materialisation step.

## Local operation

```bash
export NETA_DATABASE_URL="postgresql+psycopg://neta:neta@localhost:5432/neta"
export NETA_BACKEND_DATABASE_URL="postgresql+asyncpg://neta:neta@localhost:5432/neta"

uv run neta migrate
uv run alembic -c backend/database/alembic.ini upgrade head
uv run neta seed
uv run neta-orchestrator register-manifests
uv run dagster dev -p 3002 -m neta_orchestration.definitions
```

Register manifests once per deployed Git revision before enabling the Dagster sensor. The command uses
`NETA_GIT_COMMIT_SHA` when set and otherwise records the repository's current `HEAD`. It never alters Git.

The generated jobs cannot be launched directly from the Dagster UI without a `pipeline_run` tag. This is
intentional: scheduled, run-now, replay, retry, and backfill executions must first cross the audited
control-plane boundary. The authenticated admin API is the supported path for creating those commands.

## Adding another executable source

1. Implement or migrate its raw adapter and deterministic parser using the standard `RawArtifact`
   boundary.
2. Add a strict `Mapping[str, Any]` runner under `neta_ingest` that validates operator/backfill
   parameters and invokes the idempotent canonical pipeline.
3. Set `orchestration.runner` and `orchestration.raw_history` in the source manifest.
4. Add offline adapter/parser/runner fixtures. CI validates all manifests and loads the complete Dagster
   definition graph, so an invalid import or duplicate definition cannot merge.
5. Register the deployed manifest revision. The control plane preserves explicit admin overrides while
   rebasing unchanged fields onto the new Git defaults.

Use dlt for schema-aware structured history and incremental API/bulk resources where it provides real
value. Browser, document, feed, and gated adapters still share the envelope contract; they are not forced
through dlt extraction. See the official [Dagster asset documentation](https://docs.dagster.io/) and
[dlt pipeline documentation](https://dlthub.com/docs/general-usage/pipeline) for the underlying runtimes.
