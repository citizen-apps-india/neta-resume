# AGENTS.md

**Start with [`CLAUDE.md`](./CLAUDE.md)** — it is the agent onboarding doc: the four-layer architecture
(ingestion → Postgres → api → web), how to run each layer locally, the Typer CLI + pipeline run order,
the provenance + idempotency rules, testing commands, the data-handling ethic, and the gotchas.

Per-area notes:

- **Schema / data model** — `docs/DATA_DICTIONARY.md` (per-table reference + enums), `docs/schema.md`,
  `db/schema.dbml`. Source of truth is `db/migrations/*.sql`.
- **Running pipelines / backfills / recovery** — `docs/OPERATIONS.md`.
- **Deploying to AWS** — `docs/DEPLOYMENT.md` (env-var mapping, secrets, read-only DB role, photo-cache caveat).
- **Sources, licensing, ethics** — `docs/data-sources.md`, `docs/data-license.md`, `docs/severity-rubric.md`.
- **Entity resolution** — `docs/entity-resolution.md`.

**Rule of thumb:** stay in one layer; `web → api` over HTTP only; `ingestion` writes, `api` reads;
every fact carries a `source_ref`. Never assert guilt on criminal data; missing data renders `—`, never 0.
