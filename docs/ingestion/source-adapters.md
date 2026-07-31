# Source adapter boundary

Source adapters retrieve source-native resources and stop at an immutable raw artifact. They do not
parse domain entities or write canonical tables.

```text
validated manifest + run context
              │
              ▼
        source adapter ──fetches──▶ upstream resource
              │
              ├──stores──▶ content-addressed raw object
              │
              └──emits───▶ RawArtifact(payload, RawEnvelope, provenance_ref)
                                      │
                                      ▼
                              source converter/parser
                                      │
                                      ▼
                              canonical changes/writes
```

This boundary lets the execution engine retry extraction, detect unchanged content, inspect licensing,
and replay a stored response without coupling those operations to a parser or database transaction.

## Contract

`neta_core.pipeline.extraction` provides:

- `SourceAdapter[Request]`: the executable `extract(request, context=...)` protocol;
- `ExtractionContext`: the validated `SourceManifest`, durable run ID, clock, and raw object store;
- `HttpSourceAdapter`: the shared transport for API, crawl, and feed GET resources;
- `RawObjectStore`: the storage port implemented by the local cache and S3-compatible evidence store;
- `RawArtifact`: raw bytes, a `RawEnvelope`, and the optional compatibility pointer stored in
  `source_ref.raw_payload_ref`.

Every envelope includes source and native IDs, source URI, fetch time, content type and SHA-256, object
URI, the source-rights snapshot, pipeline run ID, and useful HTTP change metadata such as ETag or Last-
Modified. The envelope ID and object address are deterministic for the same source-native record and
content hash; a repeated fetch therefore reuses the same raw object.

The adapter rejects a request when its source ID does not match the manifest in its execution context.
This prevents a job from accidentally applying one source's licensing or runtime policy to another
source's data.

When a manifest sets `rights.store_raw: false`, extraction does not call the durable object store. The
artifact remains available to the current converter, its envelope uses an explicit `transient://` URI,
and its legacy provenance pointer is `None`. This makes the retention rule enforceable rather than only
descriptive.

## Implemented source paths

The existing canonical parsers and writes are unchanged. These live paths now make extraction explicit:

| Family | Source | Raw native unit | Existing conversion retained |
| --- | --- | --- | --- |
| API | World Bank indicators | country + indicator response | null years stay absent; series parser |
| API | Digital Sansad members | one LS/RS roster page | member and office-term parser |
| API | Digital Sansad committees | committee index or one committee roster | membership parser |
| Crawl | MyNeta | winners, constituency discovery, or candidate page | affidavit/criminal parser |
| Crawl | PRS MP Track | one listing page or member profile | activity/attendance/record parsers |
| Feed | Google News | legislator query feed | citation metadata parser |

All repository call sites for MyNeta, Digital Sansad, and PRS provide a manifest-backed execution
context; their clients no longer expose a direct-fetch fallback. Other source families such as
data.gov.in continue through the legacy `cache_raw` helper until migrated. The Dagster execution scope
now propagates its durable run key through these contexts and observes every emitted artifact. dlt
catalogues envelope metadata after the idempotent canonical write; it never bypasses this extraction
boundary or stores a prohibited response body.

## Adding or migrating a source

1. Add and validate its YAML manifest under `ingestion/source_registry/`. Identity, rights, adapter kind,
   defaults, guardrails, converter, contract, and quality requirements belong there.
2. Describe one source-native request with a stable `native_id`. Use `HttpSourceAdapter` when normal HTTP
   is sufficient; implement `SourceAdapter` for document, bulk, browser, or gated transports.
3. Keep extraction free of domain parsing and database writes. It must return `RawArtifact` after the raw
   object has been stored successfully.
4. Convert `RawArtifact.payload` with a deterministic parser. Preserve the artifact's envelope as evidence
   for every emitted canonical change and keep missing values unknown rather than coercing them to zero.
5. Add offline contract fixtures that cover envelope provenance, content-addressed idempotency, parsing,
   licensing restrictions, and malformed/empty upstream responses.
6. Register the manifest-backed asset with the orchestrator after the source works locally. Scheduling,
   pause/resume, frequency, retries, and backfills come from the control plane, not source code.

The local store writes `raw-cache://<sha-prefix>/<sha>.<ext>` objects. Kubernetes selects
`S3RawObjectStore` with `NETA_RAW_STORE_BACKEND=s3`; it writes
`s3://<bucket>/<prefix>/<sha-prefix>/<sha>.<ext>`, records the SHA-256 as object metadata, verifies existing
objects before reuse, and revalidates the payload when replayed. Both retain the same relative
`provenance_ref`, so source clients and canonical writers do not change. AWS S3 authentication uses the
pod's workload identity; `NETA_RAW_S3_ENDPOINT_URL` allows the same contract to target a compatible
open-source object store.
