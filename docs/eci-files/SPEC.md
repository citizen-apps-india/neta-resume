# ECI Files — build spec

ECI Files is a hidden, sourced, dated record of the Election Commission of India from 2019 to today. Stance
and sourcing rules are in `data/eci_files/research/BRIEF.md`; read its "stance" section. This spec covers
the software only.

It is a **source like any other**. It is registered with the ingestion control plane, it shows on the admin
console, it is loaded by a runner, it is stored in Postgres with a `source_ref` for every citation, it is read
by the public API, and it is rendered by the website. The one difference from other sources is that its
input is reviewed data files in the repo, not a remote site. Nothing scrapes at load time.

Launch is gated. The pages exist, but they are unlinked, `noindex`, and left out of `sitemap.ts` until the
owner approves.

## 1. Input: reviewed data files

The loader reads `data/eci_files/entries/*.json`. Each file has the research format from BRIEF.md
(`{"area", "entries": [...], "gaps": [...]}`). Every entry has one extra required field:

- `check`: `"checked"` | `"unchecked"`. Checked means a fact-checker opened the sources and confirmed or corrected the entry.

Entries marked `"exclude": true` are skipped. Entry ids are unique across all files, and the loader fails
loudly on a duplicate id. Tests use a small fixture under `ingestion/tests/fixtures/eci_files/`. Do not
depend on the real data files, which are being reconciled in parallel.

## 2. Storage: Alembic revision `eci_files_0004`

The revision goes under `backend/database/migrations/versions/0005_eci_files.py`, with
`down_revision = "drop_news_item_0003"`. New tables live in Alembic now; the legacy SQL migrations are frozen.

```
eci_file_entry
  id              text PRIMARY KEY            -- entry id from the data file
  area            text NOT NULL
  kind            text NOT NULL CHECK (kind IN ('event','person','rule','figure','case','statement'))
  date            date                        -- first day of the period when precision is month/year
  date_precision  text NOT NULL CHECK (date_precision IN ('day','month','year'))
  title           text NOT NULL
  summary         text NOT NULL
  status          text NOT NULL CHECK (status IN ('documented','reported','claim','response'))
  attributed_to   text
  topics          text[] NOT NULL DEFAULT '{}'
  states          text[] NOT NULL DEFAULT '{}'
  figures         jsonb NOT NULL DEFAULT '[]'
  details         jsonb NOT NULL DEFAULT '{}'
  response_to     text                        -- entry id; not an FK (load order is free)
  notes           text
  check_status    text NOT NULL CHECK (check_status IN ('checked','unchecked'))
  loaded_at       timestamptz NOT NULL DEFAULT now()
  INDEX (date), INDEX USING gin (topics)

eci_file_person
  slug            text PRIMARY KEY            -- slugify(name): lowercase, non-alnum -> '-'
  name            text NOT NULL
  profile_entry_id text REFERENCES eci_file_entry(id) ON DELETE SET NULL   -- the kind='person' entry, if any

eci_file_entry_person
  entry_id        text NOT NULL REFERENCES eci_file_entry(id) ON DELETE CASCADE
  person_slug     text NOT NULL REFERENCES eci_file_person(slug) ON DELETE CASCADE
  PRIMARY KEY (entry_id, person_slug)
  INDEX (person_slug)

eci_file_citation
  id              bigserial PRIMARY KEY
  entry_id        text NOT NULL REFERENCES eci_file_entry(id) ON DELETE CASCADE
  position        smallint NOT NULL
  source_ref_id   bigint NOT NULL REFERENCES source_ref(id)
  publisher       text
  title           text
  published       date
  tier            smallint NOT NULL CHECK (tier IN (1,2,3))
  archive_url     text
  quote           text CHECK (quote IS NULL OR length(quote) <= 200)
  UNIQUE (entry_id, position)
  INDEX (entry_id), INDEX (source_ref_id)
```

The `source_ref_id` index matters. See revision `drop_news_item_0003` for what unindexed references to
`source_ref` cost.

The downgrade drops the four tables. `alembic check` must stay clean, since these tables are not in
`MANAGED_TABLES`.

## 3. Sources: seeds

Add three rows to `db/seeds/sources.sql`, in the same style:

| code | name | license | trust_tier |
| --- | --- | --- | --- |
| `eci_files_primary` | ECI Files: official documents | public-official | 1 |
| `eci_files_research` | ECI Files: research bodies and filings | reported | 2 |
| `eci_files_press` | ECI Files: press reports | reported | 3 |

Each citation's source_ref goes under the code matching its tier, with `native_id = url` and
`native_url = url`, recorded via `neta_core.provenance.record_source_ref`.

## 4. The source manifest: `ingestion/source_registry/eci_files_curated.yaml`

Model it on `myneta_candidates.yaml`:

- `id: eci_files.curated`
- `source_code: eci_files_primary`
- `display_name: ECI Files: curated record`
- `publisher: neta-resume editorial (from cited public sources)`
- `lifecycle: active`
- `authority.role: secondary`, trust tier 2
- `ingestion.adapter: document`
- `trigger: {mode: manual, profile: editorial-review}`
- `change_detection: [content_hash]`
- `defaults: {enabled: true, paused: false, frequency_seconds: null, concurrency_limit: 1, rate_limit_per_minute: 1, retry_limit: 1}`
- guardrails with null frequencies, `max_concurrency: 1`, `max_rate_limit_per_minute: 1`, `max_retry_limit: 2`
- `conversion: {converter: neta_ingest.pipelines.curated.eci_files:load, contract: eci_file_entry.v1, produces: [eci_file_entry]}`
- `quality: {freshness_slo_seconds: null, minimum_records: 1, required_fields: [id, date, title, summary, status, sources]}`
- `orchestration: {runner: neta_ingest.runners:run_eci_files, raw_history: dlt}`
- `verification: {corroborate_with: [], human_review_required: true}`

Update `ingestion/tests/test_pipeline_contracts.py` and `orchestration/tests/test_definitions.py` for the new
manifest. The first has the expected manifest set; the second has the expected Dagster job list, which gains
`ingestion/canonical__eci_files__curated`.

## 5. The loader: `ingestion/neta_ingest/pipelines/curated/eci_files.py`

`run(path: str | Path = <repo>/data/eci_files/entries) -> None`

1. Read every `*.json` file and validate each entry with a pydantic model. Reject a missing source, an unknown status, a bad date, a duplicate id, or a quote over 15 words. Collect every error and raise them all at once.
2. In one `session_scope()`, do a full replace: delete from `eci_file_citation`, `eci_file_entry_person`, `eci_file_person` and `eci_file_entry`, then insert. The data files are the truth, so an entry removed from the files disappears. This is idempotent.
3. For each person name, upsert `eci_file_person`, setting `profile_entry_id` to the `kind=person` entry whose `details` describe that name. Match the person entry's own `people[0]` or title.
4. Print a one-line summary: entries, people, citations, checked vs unchecked.

Also wire it up in these places:
- **CLI:** add `neta eci-files` to `ingestion/neta_ingest/cli.py`, next to the other commands.
- **Runner:** add `run_eci_files(parameters)` to `ingestion/neta_ingest/runners.py`, with an `EciFilesParameters` model that has no fields, so extra keys are forbidden.
- **Tests:** `ingestion/tests/test_eci_files.py`. Validation rejects each bad case. Loading the fixture twice leaves the same row counts. Citations get the right source code per tier. Person linking works. The Postgres test is skipped when `NETA_TEST_DATABASE_URL` is unset, the same pattern as `backend/tests/test_pipeline_service_postgres.py`.

## 6. Public API: `api/neta_api/routers/eci_files.py`

Follow the pattern of `routers/indicators.py`, with a service in `services/eci_files.py`, schemas in
`schemas.py`, and registration in `main.py`. Use the same cache headers as the other read routes.

- `GET /eci-files/timeline?topic=&person=&status=&from=&to=` returns `EciTimeline {entries: EciEntry[], topics: [{topic, count}], people: [{slug, name, count}], counts: {checked, unchecked}}`, ordered by date ascending then id.
- `GET /eci-files/people` returns `EciPersonSummary[] {slug, name, role, tenure, entry_count}`. Role and tenure come from the profile entry's `details`.
- `GET /eci-files/people/{slug}` returns `EciPersonPage {person: {slug, name, profile: EciEntry | null}, entries: EciEntry[]}`, or 404.
- `GET /eci-files/entries/{id}` returns `EciEntry`, or 404.

`EciEntry` has: `id, area, kind, date, date_precision, title, summary, status, attributed_to, topics, states,
figures, details, notes, check_status, people: [{slug, name}], response_to, responses: [{id, title, date}]`
(the entries whose `response_to` is this id), and `citations: [{position, url, publisher, title, published,
tier, archive_url, quote}]`.

Add API tests if the api project has a test pattern. If not, keep the service small, and make sure `ruff check` and the requirements.txt check pass.

## 7. Website: `web/src/app/eci-files/`

The website talks to the API only, through new functions in `web/src/lib/api.ts`. Regenerate
`src/types/api.ts` from the API's OpenAPI once §6 exists. Until then, write the types by hand to match §6.

- **`/eci-files`:** a short intro saying what this is and the sourcing rules in two sentences, then the timeline.
  - Group entries by year, then by month.
  - Each entry shows its date (honouring precision, e.g. "Jul 2026"), title, summary, and a status chip. The chips read Document, Reported, Claim or Response, each a distinct token colour.
  - People appear as links. Citations are listed with publisher and tier.
  - A response appears indented under the entry it answers.
  - A "not yet checked" badge appears when `check_status = unchecked`.
  - Filters for topic and person.
- **`/eci-files/people`:** a card per person with role and tenure.
- **`/eci-files/people/[slug]`:** the profile, with career lines and their source links, followed by that person's timeline.
- **Every page:**
  - `export const metadata = { robots: { index: false, follow: false } }`. Not in `sitemap.ts`. Not linked from `SiteHeader` or the homepage.
  - Use the existing components and tokens (`SiteHeader`, `SectionHero`, `SourceLink`, `var(--...)` tokens). No hard-coded colours.
  - Works at 400px width.
  - Missing data renders as `—`.
  - No verdict words in UI copy.
- `npm run lint`, `npm run typecheck` and `npm run build` must pass.

## 8. Docs

Add a short section to `docs/OPERATIONS.md` on how to load ECI Files: edit the files, open a PR, then after
merge press Run on the `eci_files.curated` source in the admin console, or run `neta eci-files`. Add a row to
`docs/data-sources.md`. The same commit as the code, per house rules.
