# Operations runbook

Running, backfilling, and debugging the ingestion pipelines. Everything here assumes
`NETA_DATABASE_URL` is exported and you're in `ingestion/` (`uv sync` once). All pipelines are
**idempotent** (upsert on natural keys), so any step is safe to re-run.

## Full pipeline execution order

```bash
# 0. schema + seeds (once per DB):
#    uv run neta migrate     # applies pending db/migrations/*.sql, version-tracked in schema_migrations
#    uv run neta seed        # (re-)applies the idempotent reference seeds
#    In production this runs automatically in CI (.github/workflows/migrate.yml on merge to main).

# 1. roster
uv run neta ls-roster                       # LS roster + official photos (sansad.in)
uv run neta rajya-sabha                      # RS sitting roster + photos (no affidavit data)

# 2. affidavits + criminal (MyNeta — one page carries both)
uv run neta myneta --cycle LS2024 --limit 600   # winners; raise/clear limit for full cycle
uv run neta enrich-missing                   # backfill LS seats MyNeta omitted from its winners list

# 3. entity resolution / cross-cycle merge
uv run neta resolve                          # link unresolved source_refs → persons
uv run neta merge-cycles                     # merge incumbents across cycles + detect switches

# 4. parties + switches
uv run neta canon-parties                    # merge duplicate party records, clear false switches
uv run neta party-switch                     # (currently a stub — raises NotImplementedError)
uv run neta enrich-switches                  # attach sourced "why" narratives (trust_tier 3)

# 5. enrichment
uv run neta native-names                     # Devanagari names from Wikidata (18th LS)
uv run neta attendance --house ls            # PRS cumulative attendance %
uv run neta attendance --house rs
```

> **Note:** structural cross-cycle switch detection runs inside `merge-cycles` today; the standalone
> `party-switch` command is scaffolded and raises `NotImplementedError`. Don't block a run on it.

## Backfill recipes

- **Re-run one house roster:** `uv run neta ls-roster` or `uv run neta rajya-sabha`. Matches on
  constituency (LS) / `mpsno` and overwrites this source_ref's derived rows — no duplicates.
- **Re-run one MyNeta cycle / a few candidates:**
  `uv run neta myneta --cycle LS2019 --limit 600` or `uv run neta myneta --candidate 5083 --candidate 5395`.
  Each candidate's source_ref is wiped-and-reinserted, so partial re-runs are safe.
- **Refresh attendance for one house:** `uv run neta attendance --house ls` (or `rs`). Overwrites
  `office_term.attendance_pct`; rule-exempt members stay `NULL` (render `—`, never 0).
- **Add a new cycle (e.g. LS2019 for wealth trends):** ingest its `myneta` winners, then `merge-cycles`
  to fold incumbents into the existing persons and emit `party_switch_event`s.

## Partial-failure recovery

- Pipelines commit **per record / per session scope**, so a crash mid-run leaves earlier records written.
  Just re-run the same command — idempotency makes it a no-op for what already landed.
- `attendance` is **fault-tolerant per profile**: a slow/blocked PRS profile is logged and skipped
  (`fetch-failed` count in the summary), never aborting the run. Re-run to pick up the stragglers.
- If a wrong entity merge happens (`merge-cycles` is the highest-risk step), inspect with the SQL below;
  merges set `source_ref.person_id`, which is reversible.

## Inspecting the raw cache

Every fetched page is content-addressed under `ingestion/data/raw_cache/<aa>/<sha256>.<ext>` (gitignored,
written by `provenance.cache_raw`). The relative path is stored in `source_ref.raw_payload_ref`. To open
exactly what a fact was derived from:

```sql
SELECT raw_payload_ref FROM source_ref WHERE id = :source_ref_id;
-- then: open ingestion/data/raw_cache/<that path>
```

## Trace a displayed fact back to its source

Every fact table carries a `source_ref_id` (provenance). Example — a person's criminal cases with the
source link and the cached snapshot:

```sql
SELECT c.id, c.status, c.severity, cc.raw_section_text,
       s.code AS source, sr.native_url, sr.raw_payload_ref
FROM criminal_case c
JOIN source_ref sr ON sr.id = c.source_ref_id
JOIN source s      ON s.id  = sr.source_id
LEFT JOIN case_charge cc ON cc.criminal_case_id = c.id
WHERE c.person_id = :pid;
```

Same shape for any fact: `office_term.source_ref_id` (+ `attendance_source_ref_id`),
`affidavit.source_ref_id`, `party_affiliation.source_ref_id`,
`party_switch_event.narrative_source_ref_id`. Join `source_ref → source` for the system, `native_url` for
the live page, `raw_payload_ref` for the archived snapshot.

## Independence: the hosted DB is the source of truth

Schema and data reach the hosted Postgres **without a laptop**:

- **Schema/seeds** — `.github/workflows/migrate.yml` runs `neta migrate` + `neta seed` on every merge to
  `main` that touches `db/` (or via manual dispatch), using the **owner** DSN `NETA_MIGRATE_DATABASE_URL`.
  Migrations are version-tracked in `schema_migrations`; only pending ones apply.
- **Data** — `.github/workflows/ingest.yml` runs any pipeline directly against Neon (ingest write-role
  `NETA_DATABASE_URL`):
  - **Manual:** Actions → **ingest** → **Run workflow** → `args` = the full command, e.g.
    `attendance --house rs`, `leadership`,
    `historical-lookup DL_MCD2012 --house dl_mcd --current-cycle DL_MCD2022`,
    `myneta --cycle LS2024 --limit 600`. (Any `neta` command — not a fixed wrapper.)
  - **Scheduled:** weekly roster refresh (`ls-roster` + `rajya-sabha`, Mon 02:00 UTC); monthly attendance
    (1st, 04:00 UTC). News has its own `news.yml`. Heavy/one-off backfills: dispatch manually.
  - A `concurrency: ingest` group prevents overlapping writes.

`scripts/load_remote_db.sh` (full-replace from a local copy) is now **disaster-restore / one-time
bootstrap only** — not the routine path. Local Postgres is a dev environment; production no longer depends
on it.

> **One-time adoption** on the already-populated Neon: set both secrets, then run `neta migrate --baseline`
> against it ONCE (records all current migrations as applied without re-executing the non-re-runnable early ALTERs).
> After that, `migrate.yml` applies only genuinely new migrations.
