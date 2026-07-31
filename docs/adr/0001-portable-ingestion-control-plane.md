# ADR 0001: Portable ingestion and admin control plane

- **Status:** Accepted
- **Date:** 2026-07-31

## Context

The current ingestion layer is a collection of idempotent Typer commands scheduled by GitHub
Actions. It has strong provenance and domain-specific parsing, but schedules, retries, backfills,
freshness, and operator controls are distributed across code and workflow files. The source inventory
also spans structured APIs, HTML portals, feeds, bulk releases, official documents, and gated systems.
No single parser or extraction library correctly represents all of them.

The project needs frequent incremental refreshes, reliable replay, source licensing enforcement,
data-asset lineage, an admin layer, Kubernetes portability, and later cloud-managed substitutions.

## Decision

Adopt three explicit planes:

1. **Definition plane (Git):** source manifests, adapters, converters, contracts, defaults, safety
   guardrails, classification rules, and licensing policy.
2. **Control plane (admin):** active pause/resume state, frequency, rate limits, concurrency, retries,
   immediate runs, backfills, quarantine, and human review. Every change is an immutable revision.
3. **Execution plane:** Dagster materialises data assets in isolated Kubernetes jobs. dlt provides
   incremental API/bulk extraction; specialised adapters handle crawling, documents, feeds, and gated
   sources.

The effective runtime configuration is `current Git defaults + accumulated explicit admin overrides`.
Each admin change stores its patch and full result as an immutable revision, while a reset revision clears
the override set. Admin changes apply without a deployment. A Git deployment updates non-overridden
defaults and guardrails but does not erase active admin settings.

All adapters emit a `RawEnvelope`. Converters emit one or more `CanonicalChange` records with evidence.
Canonical history, PostgreSQL serving state, and search indexes are separate materialised assets.

## Source adapter families

| Adapter | Intended sources |
| --- | --- |
| `api` | Digital Sansad, data.gov.in, Wikidata, World Bank |
| `crawl` | MyNeta, PRS, MPLADS, government portal pages |
| `document` | ECI affidavits and official statistical reports |
| `feed` | RSS/Atom and publisher feeds |
| `bulk` | TCPD/LokDhaba, OpenSanctions, pinned repository releases |
| `gated` | eCourts and other authorised or human-mediated systems |

Standardisation occurs at the envelope and canonical-change boundaries, not by forcing unlike sources
through one extraction technology.

## Safety and governance

- Every materialised fact has at least one evidence reference.
- Source authority, transport, lifecycle, and licensing are distinct fields.
- Non-commercial and redistribution restrictions are machine-readable quality gates.
- News remains reported evidence; the pipeline stores permitted metadata and citations, not unlicensed
  article bodies.
- CAPTCHA and access controls are never bypassed.
- AI analysis is downstream, versioned, and never overwrites source facts.
- Missing values remain unknown rather than becoming zero.

## Technology direction

- Dagster OSS for asset lineage, partitions, checks, schedules, sensors, and backfills.
- dlt OSS for declarative API/bulk extraction, cursor state, and schema-aware loading.
- Crawlee/Playwright for web sources, using browser execution only when HTTP is insufficient.
- Docling for document layout, OCR, and table extraction with domain validation afterward.
- NATS JetStream and KEDA only for sources that genuinely need continuous event consumption.
- PostgreSQL for serving state; object storage/Iceberg for history; OpenSearch for search projections.
- Async FastAPI + SQLAlchemy for the private control API, with Alembic as the migration authority.
- Argo CD for Kubernetes GitOps, not data workflow orchestration.

Cloud services may replace these implementations only after preserving their contracts and providing a
measurable operational, reliability, or cost advantage.

## Consequences

- Source onboarding becomes a manifest, converter, and contract fixtures in the normal case.
- Scheduling becomes data-driven so admin frequency changes do not require a deployment.
- Existing source clients and parsers can be wrapped incrementally rather than rewritten all at once.
- The control database and private admin API become security-sensitive write surfaces.
- Operating Dagster and supporting Kubernetes components adds platform work, but removes GitHub Actions
  as the production scheduler and provides a coherent run/replay model.

## Delivery sequence

1. Land contracts, pilot manifests, validation tests, and this ADR.
2. Add Alembic-managed control-plane tables and a tested async FastAPI/SQLAlchemy service boundary.
3. Add the executable raw-object/envelope boundary and wrap representative existing source clients.
4. Add the Dagster `SourceComponent`, dlt-backed resources where useful, and runtime scheduler.
5. Add the private FastAPI admin API and UI on the control service boundary.
6. Wrap the remaining adapter families and materialise canonical history, PostgreSQL, and search
   projections.
7. Migrate the remaining source inventory, deploy the Kubernetes/GitOps platform, and retire equivalent
   cron workflows after parity.
