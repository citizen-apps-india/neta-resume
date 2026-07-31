# Source manifests and admin runtime configuration

Source manifests live in `ingestion/source_registry/`. They are version-controlled definitions of a
source resource, not mutable scheduler state. A source such as Digital Sansad can have separate
manifests for members, committees, questions, and debates when they have different contracts or
freshness requirements.

## Ownership boundary

| Git-owned manifest | Admin-owned runtime revision |
| --- | --- |
| Identity, publisher, authority, lifecycle | Enabled and paused state |
| Adapter and source URL | Active frequency |
| Trigger mode and default profile | Concurrency and rate limit |
| Converter and canonical contract | Retry limit |
| Orchestration runner and raw-history mode | Execution lifecycle |
| Licensing and redistribution policy | Immediate run/backfill requests |
| Default runtime values | Operational reason and actor |
| Safety guardrails | Immutable revision number and timestamp |

Admin frequency changes are permanent operational settings until changed again or reset to Git defaults.
They are not temporary overrides. Git deployments must preserve them.

## Effective configuration

At execution time the controller:

1. Loads and validates the Git manifest.
2. Loads the accumulated, explicitly set admin overrides for the same source ID.
3. Overlays those fields on the current Git defaults and stores the resulting scheduler snapshot atomically.
4. Validates the result against Git-owned guardrails.
5. Records the manifest hash, Git commit, admin revision, converter version, and contract version on the
   run.

The immutable revision row stores the operation, submitted patch, and its full resulting configuration.
The current state separately stores only the accumulated explicit overrides. This means a later
`paused: true` change retains an earlier frequency change; a new Git default affects fields no operator
has pinned; and a `reset` clears the overrides so present and future repository defaults take effect.
Registering a deployment only succeeds after the rebased snapshot passes the new guardrails.

For example, `digital_sansad.members` defaults to a 30-minute interval. An operator may set it to 15
minutes during a parliamentary session without a deployment. They cannot set it below the five-minute
guardrail through a normal admin change.

## Trigger semantics

- `scheduled`: requires a frequency. The controller calculates and stores `next_run_at`.
- `event`: launches from a durable event ID; it may also have a reconciliation run defined separately.
- `manual`: has no frequency and requires an authorised run request.

Frequency is stored as seconds in the contract so the execution engine is not coupled to cron syntax.
The admin UI may present friendly intervals or a validated advanced schedule editor.

## Runtime actions

The private admin layer supports:

- pause, resume, enable, and disable;
- change frequency, concurrency, rate limits, and retries;
- run now, retry, replay, and partitioned backfill;
- quarantine or release a source;
- inspect recent execution and configuration history;
- reset runtime configuration to repository defaults.

Observation/projection quarantine, entity review, raw-envelope inspection, and quality review remain
later admin capabilities; they are not implied by the source-level controls.

The admin service submits commands to the orchestration/control plane. It does not directly edit
canonical facts or search documents.

## PostgreSQL control state

Alembic revisions `pipeline_control_0001` and `pipeline_execution_0002` add five operational tables:

- `pipeline_source_state`: explicit admin overrides plus one scheduler-readable effective snapshot per
  manifest, including next-run, failure, and source-quarantine state;
- `pipeline_source_config_revision`: immutable patch history with actor, reason, manifest hash, Git
  commit, and full resulting snapshot;
- `pipeline_run_request`: idempotent run-now, retry, replay, and backfill commands;
- `pipeline_run`: every scheduled or requested execution, including its exact definition/config
  snapshot, stable Dagster run key, retry attempts, status, and timestamps;
- `pipeline_audit_event`: append-only application audit events for deployments and admin commands.

`backend/` follows the Hunr service layout: an async FastAPI lifespan owns the engine and
`async_sessionmaker`; declarative SQLAlchemy models define persistence; Alembic owns upgrades; and
`PipelineControlService` is the audited `AsyncSession` write boundary. The authenticated admin router
and Dagster controller call this service instead of writing these tables independently.

The Dagster sensor serialises claims with a PostgreSQL advisory lock, advances the next schedule only
after a durable `pipeline_run` exists, and may safely emit a pending run repeatedly because Dagster
deduplicates its stable run key. Source concurrency is enforced before a new execution is claimed.

The legacy SQL migrations through `0030` are frozen behind Alembic revision `legacy_0030`. A clean
database applies that SQL baseline first and then `alembic upgrade head`; an existing database can adopt
the no-op baseline and upgrade without replaying its existing schema.

## Validation

`neta_core.pipeline` rejects unknown keys, invalid identifiers, missing scheduled frequencies, unsafe
admin settings, empty admin revisions, and canonical changes without evidence. CI loads every manifest
in the registry so a malformed source definition cannot merge.

The pilot registry covers all six adapter families. Subsequent source migrations add manifests from the
full inventory in `docs/data-sources.md`. See [Source adapter boundary](source-adapters.md) for the
executable raw-envelope contract and source-onboarding checklist.
