# ECI Files redesign — phase 3 spec: the numbers

This is the build contract for phase 3. Read `SPEC.md` and `REDESIGN-SPEC.md` first; this builds on both.
The stance rules in `data/eci_files/research/BRIEF.md` still apply: no figure without a source, no verdict
words, and missing is never zero.

Phase 3 adds a state-by-state view of the Special Intensive Revision (SIR) figures. A reader should be able
to see which states lost how much of their roll between stages, open any state and follow its roll from
before the SIR to the final roll, and see every figure's source and every conflict the record notes.

## Decisions already made (owner, 25 Sep 2026)

- **Equal-sized state tiles. Never a geographic map.** That rules out any boundary drawing, shape file or
  projection, because of the border-depiction law. The existing `web/src/lib/geo.ts` boundary files must
  not be used here.
- **Every chart has a table view** and a "How we counted this" note.
- **Indian units**: lakh and crore, via `countIndian()` in `web/src/lib/format.ts`. Exact counts are
  formatted with `toLocaleString("en-IN")`.
- **Own ECI identity.** Phase 3 shares the site header, type faces and trust colours, and uses the
  `--eci-*` tokens.
- **Still gated.** Pages stay `noindex`/`nofollow`, unlinked from `SiteHeader` and the homepage, and out of
  `sitemap.ts`.
- **Charts are hand-built SVG**, in the style of `components/eci-files/DensityStrip.tsx` and
  `LaneTimeline.tsx`. Note that `components/resume/charts.tsx` imports Recharts, so it is not the model to
  copy. Phase 3 adds no chart library.

## What the record holds today

`data/eci_files/states.json` has 22 regions, loaded into `eci_file_state_stage` by the loader. Only the
stage rows are stored. The state-level `phase` and `notes` and each stage's `note` are dropped at load,
and phase 3 has to store them.

| Region | Phase | before | draft | final | after the final roll | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Bihar | 1 | ✓ | ✓ (rounded) | ✓ | — | ECI's zero-appeals claim is unverified |
| Andaman & Nicobar | 2 | ✓ | **computed** | — | — | no final roll in the record |
| Chhattisgarh | 2 | ✓ | ✓ | ✓ | — | |
| Goa | 2 | ✓ | ✓ | ✓ | `restored` 97 — **mistyped, see §1.3** | |
| Gujarat | 2 | ✓ | ✓ (rounded) | ✓ | — | |
| Lakshadweep | 2 | ✓ | ✓ | — | — | no final roll in the record |
| Madhya Pradesh | 2 | ✓ | ✓ | ✓ | — | |
| Puducherry | 2 | ✓ | ✓ (rounded) | ✓ | — | |
| Tamil Nadu | 2 | ✓ | ✓ | ✓ | — | |
| West Bengal | 2 | ✓ | ✓ | ✓ | appeals_filed, appeals_pending, restored | 60 lakh were under adjudication at the final roll |
| Rajasthan | 2 | ✓ | ✓ | ✓ | — | the before figure includes Anta and the draft excludes it |
| Uttar Pradesh | 2 | ✓ | ✓ | ✓ | — | |
| Kerala | 2 | ✓ | ✓ | ✓ | — | the ECI and CEO finals differ by about 98,363 |
| Odisha | 3 | ✓ | ✓ | ✓ | — | |
| Sikkim | 3 | ✓ | ✓ | ✓ | — | |
| Karnataka | 3 | ✓ | ✓ | pending | — | |
| NCT of Delhi | 3 | ✓ | ✓ | pending | — | |
| Maharashtra | 3 | ✓ (no date) | ✓ | pending | — | |
| Chandigarh | 3 | — | ✓ | ✓ | — | no pre-SIR figure |
| Mizoram | 3 | ✓ | — | — | — | |
| Manipur | 3 | ✓ | — | — | — | |
| Assam | none | — | ✓ | ✓ | — | **Special Revision, a different exercise from the SIR** |

Fourteen regions are not in `states.json` at all:

- **Phase III, with a Deccan Herald draft tally count only** (entry `numbers-phase3-draft-tally-2026-09-01`):
  Telangana, Andhra Pradesh, Jharkhand, Haryana and Punjab have a count of names left off the draft, but
  neither the before nor the draft total.
- **Phase III, with a share only:** Dadra and Nagar Haveli and Daman and Diu, and Arunachal Pradesh, have a
  percentage left off.
- **Phase III, with nothing for the region on its own:** Meghalaya and Uttarakhand. Nagaland's draft was
  due on 20 Sep 2026 and Tripura's on 21 Oct 2026.
- **Not in the SIR orders on record:** Himachal Pradesh, Jammu and Kashmir, and Ladakh.

**State names in entries are inconsistent.** `eci_file_entry.states` uses both "Andaman & Nicobar" and
"Andaman and Nicobar Islands", and both "Delhi" and "NCT of Delhi". A state filter needs one canonical name
per region, so phase 3 adds a region list with aliases (§1.1).

**Every stage value can be checked against its source.** Every non-computed stage value in `states.json`
equals a `figures[].value` in its `source_entry`, and I checked all of them. The one exception is Andaman &
Nicobar's draft, which is marked computed. Phase 3 turns this into a load-time rule (§1.4).

---

## 1. Data and storage (BACKEND worker)

### 1.1 New file `data/eci_files/regions.json`

This file lists all 36 States and UTs. It is static reference data, so the loader reads it on every run,
including fixture runs (see §1.4).

```json
{"regions": [{"slug": "andaman-and-nicobar-islands", "name": "Andaman and Nicobar Islands", "code": "AN",
              "kind": "ut", "aliases": ["Andaman & Nicobar", "Andaman and Nicobar"]}, ...]}
```

Rules:

- `slug` must equal `_slugify(name)`, the existing loader rule: lowercase, with each run of non-alphanumeric
  characters turned into `-`.
- `code` is our own two-letter tile label. It is not an ISO code.
- Names, codes and aliases are unique across the whole file.

The full list, which is also the web tile layout (§3.1):

| slug | name | code | kind | aliases | tile row | tile col |
| --- | --- | --- | --- | --- | --- | --- |
| jammu-and-kashmir | Jammu and Kashmir | JK | ut | Jammu & Kashmir | 0 | 2 |
| ladakh | Ladakh | LA | ut | | 0 | 3 |
| chandigarh | Chandigarh | CH | ut | | 1 | 1 |
| punjab | Punjab | PB | state | | 1 | 2 |
| himachal-pradesh | Himachal Pradesh | HP | state | | 1 | 3 |
| uttarakhand | Uttarakhand | UK | state | | 1 | 4 |
| arunachal-pradesh | Arunachal Pradesh | AR | state | | 1 | 8 |
| rajasthan | Rajasthan | RJ | state | | 2 | 1 |
| haryana | Haryana | HR | state | | 2 | 2 |
| delhi | Delhi | DL | ut | NCT of Delhi, National Capital Territory of Delhi | 2 | 3 |
| uttar-pradesh | Uttar Pradesh | UP | state | | 2 | 4 |
| bihar | Bihar | BR | state | | 2 | 5 |
| sikkim | Sikkim | SK | state | | 2 | 6 |
| assam | Assam | AS | state | | 2 | 7 |
| nagaland | Nagaland | NL | state | | 2 | 8 |
| gujarat | Gujarat | GJ | state | | 3 | 1 |
| madhya-pradesh | Madhya Pradesh | MP | state | | 3 | 2 |
| chhattisgarh | Chhattisgarh | CG | state | | 3 | 3 |
| jharkhand | Jharkhand | JH | state | | 3 | 4 |
| west-bengal | West Bengal | WB | state | | 3 | 5 |
| meghalaya | Meghalaya | ML | state | | 3 | 7 |
| manipur | Manipur | MN | state | | 3 | 8 |
| dadra-and-nagar-haveli-and-daman-and-diu | Dadra and Nagar Haveli and Daman and Diu | DD | ut | Dadra & Nagar Haveli and Daman & Diu, DNH&DD | 4 | 1 |
| maharashtra | Maharashtra | MH | state | | 4 | 2 |
| telangana | Telangana | TG | state | | 4 | 3 |
| odisha | Odisha | OD | state | Orissa | 4 | 4 |
| tripura | Tripura | TR | state | | 4 | 7 |
| mizoram | Mizoram | MZ | state | | 4 | 8 |
| goa | Goa | GA | state | | 5 | 1 |
| karnataka | Karnataka | KA | state | | 5 | 2 |
| andhra-pradesh | Andhra Pradesh | AP | state | | 5 | 3 |
| lakshadweep | Lakshadweep | LD | ut | | 6 | 0 |
| kerala | Kerala | KL | state | | 6 | 2 |
| tamil-nadu | Tamil Nadu | TN | state | | 6 | 3 |
| puducherry | Puducherry | PY | ut | Pondicherry | 6 | 4 |
| andaman-and-nicobar-islands | Andaman and Nicobar Islands | AN | ut | Andaman & Nicobar, Andaman and Nicobar | 6 | 7 |

That is 28 states and 8 UTs on a grid of 9 columns by 7 rows. The grid has gaps on purpose: (3,6) is
Bangladesh, (6,1) is sea, and (5,4)–(5,8) and (6,5)–(6,6) are the bay. The layout mirrors geography
roughly. Every tile is the same size.

### 1.2 Edits to `data/eci_files/states.json`

Make only these edits. Change no figure.

1. **`exercise`.** Add an optional per-region field, `"exercise": "sir" | "special_revision" | null`. A
   missing field means `"sir"`. Set `"exercise": "special_revision"` on Assam.
2. **`approx`.** Add an optional per-stage field, `"approx": true`, where the source gives only a rounded
   figure. Set it on three stages: Bihar draft (72,400,000, "more than 7.24 crore"), Gujarat draft
   (43,400,000) and Puducherry draft (918,000).
3. **Goa `restored`.** Remove Goa's `restored` stage. Its own note says that 97 is the number left off the
   final roll, not a restored count, so a "Restored after appeal: 97" bar would state something the record
   does not. Append its note text, unchanged, to Goa's state-level `notes`, prefixed "Separately: ". See
   open question 3.
4. **Fourteen new region rows, with `"stages": []`**, so every region has a phase and a plain-language
   note. Use these notes verbatim. The entry ids in parentheses become drawer links on the web (§3.6).

| state | phase | exercise | notes |
| --- | --- | --- | --- |
| Telangana | 3 | sir | Draft roll published. Deccan Herald's Phase III tally (1 Sep 2026) gives 73,39,235 names left off the draft (21.69% of the pre-SIR roll) but not the roll totals; the CEO's own press note was not opened (numbers-phase3-draft-tally-2026-09-01). |
| Andhra Pradesh | 3 | sir | Draft roll published. Deccan Herald's Phase III tally (1 Sep 2026) gives 44,89,512 names left off the draft but not the roll totals; the CEO's own press note was not opened (numbers-phase3-draft-tally-2026-09-01). |
| Jharkhand | 3 | sir | Draft roll published. Deccan Herald's Phase III tally (1 Sep 2026) gives 43,61,987 names left off the draft but not the roll totals; the CEO's own press note was not opened (numbers-phase3-draft-tally-2026-09-01). |
| Haryana | 3 | sir | Draft roll published. Deccan Herald's Phase III tally (1 Sep 2026) gives 33,83,302 names left off the draft but not the roll totals; the CEO's own press note was not opened (numbers-phase3-draft-tally-2026-09-01). |
| Punjab | 3 | sir | Draft roll published. Deccan Herald's Phase III tally (1 Sep 2026) gives 20,66,635 names left off the draft but not the roll totals; the CEO's own press note was not opened (numbers-phase3-draft-tally-2026-09-01). |
| Dadra and Nagar Haveli and Daman and Diu | 3 | sir | Draft roll published. Deccan Herald's Phase III tally (1 Sep 2026) gives 29.64% of the pre-SIR roll left off the draft, without the counts (numbers-phase3-draft-tally-2026-09-01). |
| Arunachal Pradesh | 3 | sir | Draft roll published. Deccan Herald's Phase III tally (1 Sep 2026) gives 19.09% of the pre-SIR roll left off the draft, without the counts (numbers-phase3-draft-tally-2026-09-01). |
| Meghalaya | 3 | sir | Included in Deccan Herald's Phase III draft tally of 17 States/UTs (1 Sep 2026), but no figure for Meghalaya on its own is in the record (numbers-phase3-draft-tally-2026-09-01). |
| Uttarakhand | 3 | sir | Included in Deccan Herald's Phase III draft tally of 17 States/UTs (1 Sep 2026), but no figure for Uttarakhand on its own is in the record (numbers-phase3-draft-tally-2026-09-01). |
| Nagaland | 3 | sir | The draft roll was due on 20 September 2026 and is not in the record's tallies (numbers-phase3-draft-tally-2026-09-01). |
| Tripura | 3 | sir | As of 1 September 2026 the draft roll was due on 21 October 2026 (numbers-phase3-draft-tally-2026-09-01). |
| Himachal Pradesh | null | null | Not in the SIR orders in the record. PTI (11 Apr 2026) described a planned Phase III including Himachal Pradesh; the ECI order of 14 May 2026 does not list it (numbers-phase3-announced-2026-05-14). |
| Jammu and Kashmir | null | null | Not in the SIR orders in the record. PTI (11 Apr 2026) described a planned Phase III including Jammu and Kashmir; the ECI order of 14 May 2026 does not list it (numbers-phase3-announced-2026-05-14). |
| Ladakh | null | null | Not in the SIR orders in the record. PTI (11 Apr 2026) described a planned Phase III including Ladakh; the ECI order of 14 May 2026 does not list it (numbers-phase3-announced-2026-05-14). |

After these edits, `states.json` has exactly 36 regions.

### 1.3 New file `data/eci_files/national.json`

These are the national totals the record itself carries. They are never sums made from the tiles, except
the one row marked computed, which is the record's own "our sum" figure.

```json
{"figures": [{"group": "all|phase_1|phase_2|phase_3", "measure": "before|draft|final|left_off|net_fall",
              "label": "...", "scope": "...", "electors": 0, "as_of": "YYYY-MM-DD", "computed": false,
              "approx": false, "source_entry": "<entry id>", "note": "... or null"}]}
```

Write exactly these 14 rows, in this order. The position in the file is the display order.

| # | group | measure | label | scope | electors | as_of | computed | approx | source_entry | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | all | left_off | More than 13 crore names left off SIR draft rolls | 30 States/UTs | 130000000 | 2026-09-23 | false | true | numbers-nationwide-13-crore-draft-exclusions-2026-09-23 | The Indian Express's figure. It leaves out Assam's Special Revision, and Nagaland and Tripura, whose drafts were still due. |
| 2 | all | left_off | Our sum of the cited draft-stage figures | 30 States/UTs | 133684385 | 2026-09-01 | true | false | numbers-nationwide-13-crore-draft-exclusions-2026-09-23 | Adds Bihar (65 lakh, rounded), the 12 Phase II state figures and Deccan Herald's Phase III tally. ECI has not published a national total that we could find. |
| 3 | phase_1 | before | Electors before the SIR | Bihar | 78969844 | 2025-06-24 | false | false | numbers-bihar-roll-base-2025-06-24 | null |
| 4 | phase_1 | draft | Electors in the draft roll | Bihar | 72400000 | 2025-08-01 | false | true | numbers-bihar-draft-roll-2025-08-01 | ECI gave the draft as "more than 7.24 crore". |
| 5 | phase_1 | left_off | Not carried into the draft | Bihar | 6500000 | 2025-08-01 | false | true | numbers-bihar-draft-roll-2025-08-01 | From ECI's outcome table, rounded to the lakh. |
| 6 | phase_1 | final | Electors in the final roll | Bihar | 74192357 | 2025-09-30 | false | false | numbers-bihar-final-roll-2025-09-30 | Excludes 1,63,619 service voters. |
| 7 | phase_2 | before | Electors before the SIR | 12 States/UTs | 509972687 | 2025-10-27 | false | false | numbers-phase2-roll-base-2025-10-27 | ECI's bulletin total. |
| 8 | phase_2 | left_off | Left off the draft rolls | 12 States/UTs | 65600000 | 2026-01-08 | false | false | numbers-phase2-draft-tally-2026-01-08 | Deccan Herald's tally of state figures, not an ECI total. |
| 9 | phase_2 | draft | Electors in the draft rolls | 12 States/UTs | 444000000 | 2026-01-08 | false | true | numbers-phase2-draft-tally-2026-01-08 | Deccan Herald's tally, not an ECI total. |
| 10 | phase_2 | final | Electors in the final rolls | 12 States/UTs | 458100000 | 2026-04-11 | false | false | numbers-phase2-final-tally-2026-04-11 | PTI's computation from EC and state data, not an ECI total. |
| 11 | phase_2 | net_fall | Net fall from the pre-SIR rolls | 12 States/UTs | 51800000 | 2026-04-11 | false | true | numbers-phase2-final-tally-2026-04-11 | PTI: "over 5.18 crore". |
| 12 | phase_3 | before | Electors before the SIR | 17 of 19 States/UTs | 360807394 | 2026-09-01 | false | false | numbers-phase3-draft-tally-2026-09-01 | Deccan Herald's tally; Nagaland and Tripura drafts not yet included. |
| 13 | phase_3 | draft | Electors in the draft rolls | 17 of 19 States/UTs | 299300115 | 2026-09-01 | false | false | numbers-phase3-draft-tally-2026-09-01 | null |
| 14 | phase_3 | left_off | Left off the draft rolls | 17 of 19 States/UTs | 61507279 | 2026-09-01 | false | false | numbers-phase3-draft-tally-2026-09-01 | null |

Every one of these `electors` values appears as a `figures[].value` in its source entry. §1.4 enforces
that.

### 1.4 Loader changes: `ingestion/neta_ingest/pipelines/curated/eci_files.py`

The new signature is:

```python
run(path=None, states_path=None, headline_path=None, regions_path=None, national_path=None)
```

- **Regions file.** `regions_path` defaults to `DEFAULT_REGIONS_PATH` (`data/eci_files/regions.json`)
  **always**, even when `path` points at a fixture, because it is reference data.
- **National file.** `national_path` follows the `states_path` rule: it is loaded only with the default
  `path` or when given explicitly.

New pydantic models, all with `extra="ignore"`:

- `EciRegion`: `slug`, `name`, `code` (pattern `^[A-Z]{2}$`), `kind` (`state|ut`) and `aliases: list[str]`.
- `EciState`: `state`, `phase: int | None` (1–3), `exercise: Literal["sir","special_revision"] | None = "sir"`,
  `notes: str | None` and `stages: list[EciStateStage]`.
- `EciStateStage` gains `note: str | None = None` and `approx: bool = False`.
- `EciNationalFigure` mirrors §1.3.

**Name resolution.** Build a map from `name`, and from each alias, to the region slug, keyed on the
casefolded name. Use it for:

- **each entry's `states`:** rewrite every value to the canonical `name` before insert, keeping order and
  deduplicating. An unknown name is a validation error:
  `"<file>: <id>: unknown state/UT 'X' (add it to regions.json aliases)"`;
- **each `states.json` `state`:** resolve it to `region_slug`, with the same error if unknown.

**Validation errors.** These are collected with every other error and raised together, as today:

- `regions.json`:
  - the count is not 36;
  - a slug, name, code or alias is duplicated;
  - a `slug` is not `_slugify(name)`.
- `states.json`:
  - a region appears twice;
  - a stage appears twice within one region;
  - a `source_entry` is not a loaded entry id;
  - a stage with `computed: false` has an `electors` value that is not in that entry's `figures[].value`
    set;
  - a phase is outside 1–3 or null.
- `national.json`:
  - an unknown group or measure;
  - a `source_entry` is not a loaded entry id;
  - an `electors` value with `computed: false` is not in that entry's `figures[].value` set. The
    `computed: true` row must also match, because the record carries it as a figure.

**Full replace order.**

- Delete: `eci_file_national_figure`, `eci_file_state_stage`, `eci_file_state`, then the existing tables,
  then `eci_file_region`.
- Insert: `eci_file_region` first, then entries, with `states` canonicalised, and the rest as today, then
  `eci_file_state`, `eci_file_state_stage` and `eci_file_national_figure`.

**Summary lines.** Add `[eci-files] loaded 36 regions, N states with figures, M national figures`.

**Fixture updates.** `ingestion/tests/fixtures/eci_files/extra/states.json` points stage values at the
fixture entry `sir-rules-2025-notification`. Add matching `figures` values (72400000, 78900000) to that
fixture entry so the new source-figure check passes. The `before` stage there is `computed: true`, so only
72400000 is strictly required, but add both.

### 1.5 Alembic revision `eci_files_states_0006`

The file is `backend/database/migrations/versions/0007_eci_files_states.py`, with
`down_revision = "eci_files_lane_0005"`. There are no SQLAlchemy models, as with 0005 and 0006: these
tables are outside `MANAGED_TABLES`, and `alembic check` stays clean.

```
eci_file_region
  slug      text PRIMARY KEY
  name      text NOT NULL UNIQUE
  code      text NOT NULL UNIQUE CHECK (code ~ '^[A-Z]{2}$')
  kind      text NOT NULL CHECK (kind IN ('state','ut'))
  aliases   text[] NOT NULL DEFAULT '{}'

eci_file_state
  region_slug text PRIMARY KEY REFERENCES eci_file_region(slug) ON DELETE CASCADE
  phase       smallint CHECK (phase IS NULL OR phase IN (1,2,3))
  exercise    text CHECK (exercise IS NULL OR exercise IN ('sir','special_revision'))
  notes       text

eci_file_state_stage   -- altered
  DELETE all rows first (derived, full-replace data; re-run `neta eci-files` after upgrading)
  DROP INDEX ix_eci_file_state_stage_state; DROP COLUMN state
  ADD region_slug text NOT NULL REFERENCES eci_file_state(region_slug) ON DELETE CASCADE
  ADD note   text
  ADD approx boolean NOT NULL DEFAULT false
  ADD UNIQUE (region_slug, stage)  -- name uq_eci_file_state_stage_region_stage
  INDEX ix_eci_file_state_stage_region (region_slug)

eci_file_national_figure
  position       smallint PRIMARY KEY
  grp            text NOT NULL CHECK (grp IN ('all','phase_1','phase_2','phase_3'))
  measure        text NOT NULL CHECK (measure IN ('before','draft','final','left_off','net_fall'))
  label          text NOT NULL
  scope          text NOT NULL
  electors       bigint NOT NULL
  as_of          date
  computed       boolean NOT NULL DEFAULT false
  approx         boolean NOT NULL DEFAULT false
  source_entry_id text NOT NULL REFERENCES eci_file_entry(id) ON DELETE CASCADE
  note           text
  INDEX (source_entry_id)

eci_file_entry
  CREATE INDEX ix_eci_file_entry_states ON eci_file_entry USING gin (states)
```

The column is named `grp`, not `group`, to avoid quoting a reserved word. The API exposes it as `group`.

**Downgrade.**

1. Drop the gin index and `eci_file_national_figure`.
2. Delete the rows in `eci_file_state_stage`.
3. Drop its unique constraint, its index, `region_slug`, `note` and `approx`.
4. Re-add `state text NOT NULL` and `ix_eci_file_state_stage_state`.
5. Drop `eci_file_state` and `eci_file_region`.

Also update `docs/OPERATIONS.md` in the same commit. Its ECI Files section should list the five input
files and say "after `alembic upgrade head` to 0007, re-run `neta eci-files`".

### 1.6 Tests: `ingestion/tests/test_eci_files.py`

Add one test per new validation rule, using `tmp_path` files:

- an unknown state name in an entry;
- an unknown state in `states.json`;
- a duplicate stage;
- a stage value missing from its entry's figures;
- a computed stage value that is exempt from the figures check;
- a duplicate region code;
- a slug that does not equal `_slugify(name)`;
- an unknown national group.

Add these tests too:

- Alias canonicalisation: an entry with `"states": ["NCT of Delhi", "Delhi"]` is stored as `["Delhi"]`.
- A Postgres test, skipped without `NETA_TEST_DATABASE_URL`:
  - after loading the fixture with explicit `states_path` and `national_path`, `eci_file_region` has 36
    rows;
  - `eci_file_state_stage.region_slug` is `bihar`;
  - loading twice leaves the same counts.
- `test_real_data_files_validate`: run the validation half, without the DB write, against the real `data/`
  files and assert no errors. This catches data drift in CI. Split validation out of `run()` into
  `validate_all(...) -> (payload, errors)` so the test can call it without a database.

---

## 2. Public API (BACKEND worker)

The files are `api/neta_api/services/eci_files.py`, `api/neta_api/routers/eci_files.py` and
`api/neta_api/schemas.py`, and the backend worker is the **only** editor of `schemas.py`. Cache headers come
from the existing `CacheControlMiddleware`, with no per-route change.

### 2.1 `GET /eci-files/states` → `EciStatesOverview`

This returns all 36 regions, sorted by `name` ascending, together with the national figures.

### 2.2 `GET /eci-files/states/{slug}` → `EciStatePage`, or 404 `"state not found"`

This returns one region with its notes. The web fetches the state's entries separately, through the
timeline's `state=` filter.

### 2.3 `GET /eci-files/timeline` gains `state=<slug>`

- **The filter.** The service resolves the slug to the canonical name through `eci_file_region` and adds
  `:state_name = ANY(e.states)`. An unknown slug returns an empty `entries` list, the same as an unknown
  person. It is not a 404.
- **A new facet.** The timeline gains `states: [{slug, name, count}]` over the whole record, ordered by
  count descending, then name. It is built from `unnest(states)` joined to `eci_file_region` on `name`.
- **Both shapes.** Add `states: list[EciStateCount] = []` to both `EciTimeline` and `EciTimelineCompact`.

### 2.4 Schemas (add to `schemas.py`)

```python
class EciStageValue(BaseModel):
    stage: str                  # before | draft | final | appeals_filed | appeals_pending | restored
    electors: int
    as_of: date | None = None
    computed: bool
    approx: bool
    note: str | None = None
    source_entry_id: str
    source_entry_title: str     # eci_file_entry.title, joined
    source_status: str          # the source entry's status: documented | reported | claim | response
    url: str
    tier: int

class EciStateMetric(BaseModel):
    value: float                # percent, rounded to 2 dp; signed for net_change
    count: int                  # electors; signed for net_change
    base: int                   # the denominator, in electors
    computed: bool              # any contributing stage is computed
    approx: bool                # any contributing stage is approx
    noted: bool                 # any contributing stage carries a note

class EciStateMetrics(BaseModel):
    draft_left_off: EciStateMetric | None = None
    net_change: EciStateMetric | None = None
    appeals_filed: EciStateMetric | None = None

class EciRegionSummary(BaseModel):
    slug: str
    name: str
    code: str
    kind: str                   # state | ut
    phase: int | None = None
    exercise: str | None = None # sir | special_revision | None (not in any exercise on record)
    has_figures: bool           # at least one stage
    entry_count: int            # entries whose states include this region (kind <> 'person')
    stages: list[EciStageValue] = []   # canonical order: before, draft, final, appeals_filed, appeals_pending, restored
    metrics: EciStateMetrics

class EciNationalFigure(BaseModel):
    group: str                  # all | phase_1 | phase_2 | phase_3
    measure: str                # before | draft | final | left_off | net_fall
    label: str
    scope: str
    electors: int
    as_of: date | None = None
    computed: bool
    approx: bool
    note: str | None = None
    source_entry_id: str
    source_entry_title: str
    source_status: str

class EciStatesOverview(BaseModel):
    regions: list[EciRegionSummary]
    national: list[EciNationalFigure]
    last_as_of: date | None = None   # max(as_of) over every stage

class EciStatePage(BaseModel):
    region: EciRegionSummary
    notes: str | None = None

class EciStateCount(BaseModel):
    slug: str
    name: str
    count: int
```

### 2.5 Derived metrics

Put the metric logic in a pure function in the service, `derive_metrics(stages: dict[str, dict],
exercise: str | None) -> dict`, with no DB access, so it can be unit-tested. When `exercise != "sir"`,
**all three metrics are null.** That keeps Assam's Special Revision out of the SIR comparison.

| metric | needs | count | base | value |
| --- | --- | --- | --- | --- |
| `draft_left_off` | before and draft | before − draft | before | round(count / base × 100, 2) |
| `net_change` | before and final | final − before (signed) | before | round(count / base × 100, 2), signed |
| `appeals_filed` | appeals_filed and final | appeals_filed | final | round(count / base × 100, 2) |

For each metric:

- `computed` is the OR of the contributing stages' `computed`;
- `approx` is the OR of their `approx`;
- `noted` is true if any contributing stage's `note` is non-null.

Metric values are never stored. They are computed on read from the stage rows.

### 2.6 API tests: new `api/tests/test_eci_state_metrics.py`

These are pure tests with no database:

- each formula;
- null when a stage is missing;
- null for `special_revision`;
- `computed` propagates;
- the sign of `net_change`.

Add `- run: uv run pytest` to the `api` job in `.github/workflows/ci.yml`, after `ruff check`. pytest is
already an api dev dependency. Regenerate `docs/eci-files/openapi.json` the way phase 2 did, by dumping
`app.openapi()`.

### 2.7 Expected values against the real data

These values double as acceptance checks.

- `/eci-files/states`:
  - `regions` has 36 rows;
  - 22 have `has_figures = true`;
  - `last_as_of` is `2026-09-22`.
- `bihar`: `draft_left_off` = {value 8.32, count 6569844, base 78969844, approx true, because the draft is
  rounded}, and `net_change` = {value −6.05, count −4777487}.
- `west-bengal`: `net_change` value is −15.9, count −12184920. `appeals_filed` = {value 5.94, count 3831429,
  base 64452609}.
- `andaman-and-nicobar-islands`: `draft_left_off` = {value 20.62, computed true}, and `net_change` is null.
- `assam`: `exercise` is `"special_revision"` and all metrics are null. `chandigarh`: all metrics null.
- `goa`: no `restored` stage.
- `delhi`: `draft_left_off` value is 32.78.
- `/eci-files/states/haryana`: `has_figures` is false, `phase` is 3, and `notes` starts "Draft roll
  published."
- `/eci-files/states/narnia` returns 404.
- `timeline?state=delhi` includes entries originally tagged "Delhi" and "NCT of Delhi".
- `timeline?state=west-bengal&fields=compact` returns exactly the entries whose `states` contain "West
  Bengal".

---

## 3. Website (WEB worker)

### 3.1 Tile layout and metric definitions: new `web/src/lib/eci-numbers.ts`

- **Region slugs.** Export `type EciRegionSlug`, a union of the 36 slugs in §1.1, and
  `isEciRegionSlug(s: string)`.
- **Tile layout.** Export `ECI_TILE_LAYOUT: Record<EciRegionSlug, { row: number; col: number }>`, taking
  the values from the table in §1.1. Using `Record` over the union means `tsc` fails if a region has no
  tile. Also export `ECI_TILE_COLS = 9` and `ECI_TILE_ROWS = 7`.
- **Metric definitions.** Export `ECI_METRICS`, an ordered array of:

```ts
{ id: "draft_left_off" | "net_change" | "appeals_filed";
  param: "left_off" | "net_change" | "appeals";        // URL ?metric=
  label: string; shortLabel: string;
  bins: number[];                                        // 4 cut points → 5 bands, lower-inclusive
  bandLabels: string[];                                  // 5 strings for the legend
  encode: (m: EciStateMetric) => number;                 // the number that is binned
  missingReason: (r: EciRegionSummary) => string;        // tile/table text when the metric is null
  howWeCounted: string; }
```

| id | label | shortLabel | encode | bins | bandLabels |
| --- | --- | --- | --- | --- | --- |
| draft_left_off | Share of the pre-SIR roll not on the draft roll | Left off the draft | `m.value` | 5, 10, 15, 20 | under 5% · 5–10% · 10–15% · 15–20% · 20% or more |
| net_change | Net change from the pre-SIR roll to the final roll | Net change to final | `-m.value` (the size of the fall) | 3, 6, 9, 12 | under 3% fall, or a rise · 3–6% fall · 6–9% fall · 9–12% fall · 12% fall or more |
| appeals_filed | Appeals filed against the final roll, as a share of it | Appeals filed | `m.value` | 1, 2.5, 5, 10 | under 1% · 1–2.5% · 2.5–5% · 5–10% · 10% or more |

`missingReason` returns the first of these that applies:

1. `"Special Revision, not SIR"` when `exercise === "special_revision"`;
2. `"no figures yet"` when there are no stages;
3. `"no pre-SIR figure"` when a needed `before` is missing;
4. `"no final roll yet"` when a needed `final` is missing;
5. `"no draft figure"`;
6. `"no appeals figure"`.

Export `bandFor(metric, value): 1 | 2 | 3 | 4 | 5`. It returns the lowest band whose upper cut point is
greater than `value`, and band 5 otherwise. A negative `encode`, which is a rise, lands in band 1.

**Tile state.** Export `tileState(region, metric)`. It returns one of:

- `{ kind: "value", band, metric }`;
- `{ kind: "no_measure", reason }`: the region has stages but not this metric;
- `{ kind: "other_exercise" }`: Assam;
- `{ kind: "no_figures", phase }`: no stages.

**Display formatting.**

- Percentages show 1 dp, for example `18.7%`. For `net_change`, show the signed value with a real minus
  sign, U+2212, for example `−13.2%`.
- Counts use `countIndian()`, for example `2.89 crore`.
- An approx or computed metric gets a trailing `*` on tiles.
- An approx stage value gets a leading `≈` in the stage chart and the table.

The `howWeCounted` copy, verbatim:

- **draft_left_off:** "The pre-SIR roll minus the draft roll, divided by the pre-SIR roll. Both figures come
  from the cited entries, and the dates differ by state. This counts names not carried into the draft. It
  is not the number finally deleted: names can return through claims before the final roll, and new
  electors are added."
- **net_change:** "The final roll minus the pre-SIR roll, divided by the pre-SIR roll. A negative number
  means the final roll is smaller. The colour shows the size of the fall; a rise would sit in the lightest
  band. Where the source says so, final rolls exclude service voters."
- **appeals_filed:** "Appeals filed against the final roll, divided by the final roll. Only West Bengal has
  an appeals figure in the record; every other tile shows no appeals figure, which is not the same as no
  appeals. An appeal can seek to restore a deleted name or to delete an included one, and ECI's count
  includes both."
- **Shared footnote,** shown under all three: "* rests on a computed or rounded figure. Andaman & Nicobar's
  draft, for example, is worked out from the pre-SIR roll and a reported removal. The state page gives the
  method."

### 3.2 Colour: tokens in `globals.css` (WEB worker is the only editor)

The ramp is a **single-hue sequential violet in 5 steps**, derived from `--eci-ink` and modelled on
ColorBrewer's single-hue *Purples*. Only lightness changes from step to step, so the order stays readable
under protanopia, deuteranopia and tritanopia, and in greyscale. Values are also printed on the tiles at
480px and up, and they are always in the table. I computed the contrasts below with the WCAG formula.

| token | light | text on it (light) | dark | text on it (dark) |
| --- | --- | --- | --- | --- |
| `--eci-seq-1` | `#F1ECF8` | `--ink` #121317 (16.0:1) | `#2A2238` | `--ink` #F3F4F6 (13.8:1) |
| `--eci-seq-2` | `#D6C8EB` | `--ink` (11.8:1) | `#46356A` | `--ink` (9.7:1) |
| `--eci-seq-3` | `#B39BD8` | `--ink` (7.9:1) | `#6B4F9E` | `--ink` (5.9:1) |
| `--eci-seq-4` | `#7A51B0` | `#FFFFFF` (5.8:1) | `#9674CC` | `#0C0D10` (5.2:1) |
| `--eci-seq-5` | `#4F2677` | `#FFFFFF` (11.2:1) | `#C7A9EE` | `#0C0D10` (9.6:1) |

- **Foreground tokens.** Add `--eci-seq-fg-1` to `--eci-seq-fg-5`, holding the text colours above, so
  components never pick a colour themselves.
- **Direction in dark mode.** Higher values are brighter in dark mode, meaning more luminous against the
  `#0C0D10` background. This is the dark-theme convention.
- **Tile borders.** Step 1 is close to the card colour (1.16:1 in light), so every tile has a
  `1px solid var(--rule)` border.

Tokens for the special tile states:

- `--eci-tile-empty-bg: var(--sunken)`, with a dashed `var(--border2)` border and text in `var(--ink2)`.
  That is 6.9:1 in light. Do not use `--muted` here, because it is 3.1:1 on the sunken background.
- The no-measure state uses `var(--card)`, a solid `var(--rule)` border, and `var(--muted)` for the reason
  text. Show `—` in `var(--ink2)`.
- The other-exercise state uses
  `repeating-linear-gradient(45deg, var(--card) 0 5px, var(--rule) 5px 6px)` with text in `var(--ink2)`.

Put the tokens in both the `:root, [data-theme="light"]` block and the `[data-theme="dark"]` block, next to
the existing `--eci-*` line. No component names a hex value.

### 3.3 `/eci-files/numbers`: new `web/src/app/eci-files/numbers/page.tsx`

- **Metadata.** `title: "The numbers · ECI Files"`, `robots: { index: false, follow: false }`.
- **Search params.** `metric` (`left_off` | `net_change` | `appeals`, default `left_off`), `view` (`tiles` |
  `table`, default unset), `entry` (drawer) and `state`. If `state` is a valid slug, `redirect()` to
  `/eci-files/numbers/{state}`. This is the no-JS path for the picker form.
- **Data.** One fetch, `getEciStates()`, inside a Suspense body with an `EciNumbersSkeleton` fallback, in
  the same pattern as `EciFrontBody`. On failure, render "The record hasn't loaded — try again in a
  moment."

The layout, top to bottom, inside `main` at `maxWidth: 1000`, using the same `main` style as the front page:

1. **`SectionHero`.**
   - eyebrow: `ECI FILES · THE NUMBERS`
   - title: `The SIR, state by state`
   - `backHref="/eci-files"` and `backLabel="ECI Files"`
   - subtitle: "Special Intensive Revision (SIR) figures for each State and Union Territory, taken from the
     cited entries in the record. The tiles are equal in size and placed roughly where the states sit; this
     is not a map. Pick a measure, or open a state to follow its roll from before the SIR to the final
     roll."
2. **`StatePicker`** (§3.5).
3. **`NationalSummary`** (§3.7).
4. **`DraftCaveat`.**
   - This is a bordered box with a left rule in `var(--eci-ink)`.
   - Title: "A draft roll is not the final roll".
   - Body: "The draft roll is published after enumeration. Names left off it can come back through claims
     and objections, and new electors are added, before the final roll is published. So the share left off
     the draft is usually larger than the net change from the pre-SIR roll to the final roll. Where a final
     roll isn't in the record yet, only the draft measure can be shown."
   - Then, in mono type: "Figures run to {formatLooseDate(last_as_of)}. Several final rolls were still
     pending then."
5. **A controls row**, which wraps:
   - **`MetricSwitch`:** three `<Link>`s styled as a segmented control (`.seg`), labelled with each
     metric's `shortLabel`. The active one has `aria-current="true"`. The links keep `view`.
   - **`ViewToggle`:** two links, "Tiles" and "Table", with `aria-current` on the active one. They keep
     `metric`.
6. **A `.eci-numbers` wrapper** with `data-view={view ?? "auto"}`, containing both `StateTileGrid` and
   `StateTable`. CSS decides which is visible: `auto` shows the tiles at 480px and up and the table below
   480px, while `tiles` and `table` force one. Both are rendered server-side, so there is no hydration
   flash.
7. **`StateTileLegend`**, followed by `HowWeCounted`: a `<details>` whose summary reads "How we counted
   this", holding the current metric's `howWeCounted` and the shared footnote.
8. **The drawer.** When `entry` is set, render `EntryDrawer` with `EntryDetail`, passing
   `basePath="/eci-files/numbers"` and preserving `metric` and `view`. This is the same pattern as the
   timeline page.

### 3.4 Components (all new, in `web/src/components/eci-files/`)

**`StateTileGrid.tsx`** (client, for keyboard)

- **Props.** `{ regions: EciRegionSummary[]; metric: EciMetricDef }`.
- **Container.** A `<div role="group">` with the aria-label "States and union territories, coloured by
  {metric.label}", laid out as a CSS grid of `repeat(9, minmax(0, 1fr))` with a 4px gap, `max-width: 720px`
  and `margin: 0 auto`.
- **Tiles.** Each tile is a `<Link href="/eci-files/numbers/{slug}">`. It is a link, not a button, because
  it navigates. It is placed with `gridRow: row + 1` and `gridColumn: col + 1`, uses `aspect-ratio: 1` and
  `border-radius: 8px`, and has class `eci-tile` plus a state modifier: `data-band="1..5"`,
  `eci-tile--nomeasure`, `eci-tile--other` or `eci-tile--empty`. Render the tiles in DOM order sorted by
  (row, col).
- **Tile content.**
  - The **code** comes first, in mono at 10–11px.
  - The **value** comes second: the metric value, the `—` for no-measure, `SR` for other-exercise, or
    nothing for empty. It is hidden under 480px.
  - A tiny **third line** appears at 640px and up. It reads "no figures yet" on empty tiles and shows the
    `missingReason` on no-measure tiles.
- **`aria-label`,** one of:
  - a value tile: "{name}: {formatted value} — {metric.label.toLowerCase()} ({countIndian(count)} of
    {countIndian(base)}). Phase {roman}. Open state page."; append " Uses a computed or rounded figure."
    when the metric is computed or approx;
  - a no-measure tile: "{name}: {reason}. Open state page.";
  - the other-exercise tile: "{name}: Special Revision, a different exercise; not compared. Open state
    page.";
  - an empty tile: "{name}: no figures yet. Open state page."
- **Keyboard.** The grid uses a roving tabindex, so exactly one tile has `tabIndex=0`, starting with the
  first tile in DOM order.
  - Arrow keys move focus to the nearest tile in that direction. Search along that axis first, then take
    the smallest perpendicular distance, and skip gaps.
  - Home and End move to the first and last tile in the current row.
  - Enter follows the link natively. Tab leaves the grid.
  - The focus ring is `outline: 2px solid var(--eci-ink); outline-offset: 2px`.
- **Readout.** A single line under the grid, marked `aria-hidden` because the focused tile's label already
  announces the same thing, shows the hovered or focused tile, for example "Uttar Pradesh · 18.7% not on
  the draft roll · 2.89 crore of 15.44 crore". When nothing is hovered, it reads "Hover or focus a tile;
  open it for the state's full journey."

**`StateTileLegend.tsx`**

- It shows 5 swatches with the metric's `bandLabels`.
- It then shows 3 swatches, one per special state: "No figures yet" (empty), "Figures on record, not this
  measure" (no-measure) and "Special Revision (Assam), not compared" (other).
- It uses `role="list"` and reuses the `.eci-legend` and `.eci-legend-item` classes.

**`StateTable.tsx`** (server)

- It is a `<table>` with the caption "SIR figures by State/UT — sorted by {metric.shortLabel}", `th
  scope="col"`, and a `th scope="row"` for the state name. The state name links to the state page.
- **Columns:**
  - State/UT;
  - Phase, as `I`, `II` or `III`, or `SR` for Assam, or `—`;
  - Before SIR;
  - Draft;
  - Final;
  - the current metric's count;
  - the current metric's %.
- Stage cells show `countIndian`, with the exact en-IN count and the as-of date in `title` and on a second
  line in mono at 10.5px. Mark approx stage values with `≈`, and put "computed" or "rounded" tags after the
  metric cell where they apply.
- **Rows:**
  - regions with the metric, sorted by the encoded value descending, then by name;
  - then regions with figures but without the metric, sorted by name, with the reason in the metric cells;
  - then a single final row spanning every column: "No figures yet in the record: Andhra Pradesh,
    Arunachal Pradesh, …", where each name links to its state page.
- **No totals row.** The national totals are the cited ones in §3.7, and sums of mixed dates are not ours
  to make.
- **Mobile.** Under 480px, hide the Before, Draft and Final columns with the `.eci-col-stage` class; the
  state page has them. The whole table sits in the existing horizontal-scroll shadow wrapper used
  elsewhere in `globals.css`.

**`StatePicker.tsx`** (server; no client JS needed)

- **The form.** It is
  `<form action="/eci-files/numbers" method="get" className="eci-picker">`, containing a
  `<label htmlFor="eci-state-picker">` that reads "What happened in my state?", a
  `<select id="eci-state-picker" name="state" className="eci-select" required>`, and a
  `<button type="submit">` that reads "Show".
- **The first option** is "Choose a State or UT", with an empty value, `disabled` and selected.
- **Two optgroups:** "With SIR figures", for regions where `has_figures`, and "No figures yet" for the
  rest. Each is sorted by name.
- **No auto-navigate on change.** Arrow keys fire change events in some browsers, so navigation waits for
  the explicit Show button.
- **Props.** `{ regions: Pick<EciRegionSummary, "slug" | "name" | "has_figures">[]; current?: string;
  compact?: boolean }`. When `current` is set, that option is pre-selected. `compact` drops the label text
  and keeps it for screen readers only, with an `.sr-only` or `aria-label`.

**`NationalSummary.tsx`** (server): see §3.7.

**`StageChart.tsx`** (server, hand-built SVG): see §3.6.

**`StateNotes.tsx`**, **`StateMetricTiles.tsx`**, **`AfterFinalFigures.tsx`** and **`DraftCaveat.tsx`**
(server): see §3.3 and §3.6.

**`HowWeCounted.tsx`** (server): a `<details>` with the summary "How we counted this".

### 3.5 The "What happened in my state?" entry points

- **Front page.** In `web/src/app/eci-files/page.tsx`, `EciFrontBody` fetches
  `Promise.all([getEciSummary(), getEciStates().catch(() => null)])`, and passes `regions` into
  `QuestionCards`.
- **Question cards.** `QuestionCards.tsx` gains a first card, "What happened in my state?", with the hint
  "Roll figures before, during and after the SIR". Its body is a `StatePicker` with `compact`.
  - If `regions` is null because the fetch failed, the card is a plain link to `/eci-files/numbers`.
  - Add another card: "How many names left the rolls?", with the hint "Every State and UT, side by side",
    linking to `/eci-files/numbers`.
- **Front-page button.** In the front page's button row, add a ghost link, "The numbers, state by state →",
  pointing to `/eci-files/numbers`.
- **The numbers page.** `/eci-files/numbers` has a full `StatePicker` under the hero (§3.3).
- **State pages.** `/eci-files/numbers/[state]` has a compact `StatePicker` with `current={slug}` under its
  hero, so a reader can hop from state to state.

### 3.6 `/eci-files/numbers/[state]`: new `web/src/app/eci-files/numbers/[state]/page.tsx`

- **Metadata.** `generateMetadata` returns `title: "{name} · The numbers · ECI Files"`, `robots: { index:
  false, follow: false }`.
- **Unknown slugs.** If `isEciRegionSlug(state)` is false, or the API returns 404, call `notFound()`.
- **Fetches, in parallel:** `getEciState(slug)`, `getEciStates()` for the picker, and
  `getEciTimelineCompact({ state: slug })`.
- **Rendering.** The page is dynamic, with no `generateStaticParams`, so the build never needs the API.

The layout:

1. **`SectionHero`.** The eyebrow is `ECI FILES · THE NUMBERS`, the title is `region.name`, and the back
   link reads "The numbers" and goes to `/eci-files/numbers`. The subtitle depends on the case:
   - **SIR with stages:** "Special Intensive Revision, Phase {roman}. {n} figures on record, from {first
     as_of} to {last as_of}." Use `formatLooseDate`, and skip null dates.
   - **Special Revision:** "Special Revision — a different exercise from the Special Intensive Revision run
     in other States. Its figures are shown here but kept out of the SIR comparisons."
   - **No stages:** "No SIR figures for {name} are in the record yet." If a phase is set, append " It is in
     Phase {roman} of the SIR."
2. **`StatePicker`**, compact.
3. **`StateMetricTiles`.** There are three tiles in `.eci-hero-tile` style, one per metric: the label, the
   value (1 dp %) and the count in lakh or crore, or `—` with the `missingReason`. The tiles are omitted
   when there are no stages.
4. **`StageChart`,** under the heading "From the pre-SIR roll to the final roll". It is omitted when none of
   before, draft or final exist.
   - **Rows.** Each row is a CSS grid, `grid-template-columns: minmax(120px, 180px) 1fr minmax(90px, auto)`:
     - **the label:** "Before the SIR", "Draft roll" or "Final roll", with the as-of date under it in mono
       at 11px;
     - **the bar:** an inline `<svg viewBox="0 0 100 14" preserveAspectRatio="none" aria-hidden>` holding
       a `<rect>` whose width is `electors / max × 100`. The scale is zero-based and `max` is the largest
       of the three;
     - **the value:** `countIndian`, prefixed with `≈` when approx.
   - **Bar fill** is `var(--eci-ink)`. A computed stage instead uses an SVG `<pattern>` hatch with
     `var(--eci-ink)` stripes on `var(--card)` and a "computed" tag after the value.
   - **Reference line.** A dashed vertical line in `var(--border2)` marks the end of the Before bar and
     runs through the Draft and Final rows, so the gap reads without arithmetic.
   - **Delta lines.** Between rows sits a mono line at 11.5px in `var(--ink2)`:
     - Before → Draft: "− {countIndian(before − draft)} not carried into the draft ({pct}%)";
     - Draft → Final: "+ {countIndian(final − draft)} between draft and final" when final > draft, and
       "− …" otherwise.
     - Use U+2212 for minus signs.
     - Omit a delta when either side is missing.
   - **Missing rows.** A missing stage renders its label, no bar, and "— not in the record yet" in
     `var(--muted)`.
   - **Source line.** Under each row: "Source: {source_entry_title} · {TIER label}". The title links to
     `?entry={source_entry_id}` on this same page and opens the drawer. The tier label reuses the
     `TIER_LABEL` wording in `CitationList.tsx`; export it from there. If the stage has a `note`, add "See
     the note below ↓".
   - **Table view.** `<details><summary>Show as a table</summary>` holds a table with the columns Stage,
     Electors (exact, en-IN), As of, Source (link), Tier, Flags (computed or rounded).
   - **"How we counted this".** Every bar starts at zero. Differences are simple subtraction of the cited
     figures. A computed stage's method is in its note.
   - **Mobile.** Under 560px, each row stacks: the label on one line, then the bar and value on the next.
5. **`AfterFinalFigures`,** under the heading "After the final roll". It is shown only if there is an
   appeals_filed, appeals_pending or restored stage.
   - Each stage is a plain figure row. The labels are "Appeals filed", "Appeals still pending" and
     "Restored after appeal".
   - A row shows the exact count, the as-of date and a source link, as in the stage chart.
   - There is no bar, because these are counts of applications and not roll sizes.
6. **`StateNotes`,** under the heading "Notes and conflicts in the record".
   - The state's `notes` paragraph comes first.
   - Then comes one paragraph per stage with a note, prefixed with the stage label in bold ("Final roll: …").
   - Render the text plainly, with no rewording.
   - **Linkify entry ids.** Linkify any token matching
     `/\b(numbers|sir-rules|officials|commissioners|courts|elections-2019-2024|selection-law|statements-reporting)-[a-z0-9-]+\b/`
     to `?entry=<token>` on this page. The drawer renders nothing if the id doesn't exist, which is
     existing behaviour.
7. **`DraftCaveat`,** the same component as in §3.3. It is shown when the region has stages.
8. **"Entries about {name}".**
   - With entries: a `LaneTimeline`. The window's `from` is the first day of the month of the earliest
     dated entry. Its `to` is the latest entry date or today, whichever is later.
   - Put `StatusLegend` above the timeline.
   - Below it, add the link "Open in the lane timeline →", pointing to
     `/eci-files/timeline?state={slug}&from=…&to=…`.
   - With no entries: "No entries name {name} yet."
9. **The drawer.** When `entry` is set, render `EntryDrawer` with `EntryDetail`, passing
   `basePath="/eci-files/numbers/{slug}"`.

### 3.7 `NationalSummary` (on `/eci-files/numbers`)

- **The "all" group.** At the top, show `group === "all"` row 1 large, as "13 crore+" with its label, then
  row 2 beneath it in smaller text. Each carries its `note`, a "Source: {source_entry_title}" link to
  `?entry=`, and a status chip reusing `StatusChip` from `source_status`.
- **Phase cards.** Below that are three cards in a grid (`repeat(auto-fit, minmax(240px, 1fr))`), titled:
  - "Phase I · Bihar";
  - "Phase II · 12 States/UTs";
  - "Phase III so far · {scope}", with the scope taken from the data.

  Each card lists its rows in file order as label and value (`countIndian`, `≈` when approx), with the
  as-of date and a source link. Notes appear as small text.
- **Phase III final line.** The Phase III card ends: "Most Phase III final rolls were not yet published at
  the last figure in the record."
- **Method line,** under the cards: "These totals are the ones the record itself carries — an ECI bulletin,
  or a newspaper's own tally — not sums we made from the tiles, except the one marked 'our sum'. Different
  tallies use different dates and bases, so they don't add up exactly."

### 3.8 Small edits to existing files (WEB worker)

- **`web/src/lib/eci-files.ts`.** Change the signature to
  `eciEntryHref(id, preserve = {}, basePath = "/eci-files/timeline")`.
- **`EntryDetail.tsx`.** Add an optional `basePath` prop and pass it through to `eciEntryHref`.
- **`web/src/app/eci-files/timeline/page.tsx`.** Accept a `state` param, pass it to
  `getEciTimelineCompact` and include it in `preserve`.
- **`Filters.tsx`.** Add an optional `states?: EciStateCount[]` and `state?: string`. When `states` is
  non-empty, render a third `FilterSelect` with id `eci-filter-state`, label "State/UT", param `state` and
  "All States/UTs". Add `state` to `cur`.
- **`web/src/lib/api.ts`** (WEB is the only editor):
  - add `state?: string` to `EciTimelineOpts`, and to `eciTimelineQuery`;
  - add `getEciStates(): Promise<EciStatesOverview>` (revalidate 3600);
  - add `getEciState(slug): Promise<EciStatePage | null>`, which returns null on 404 and throws on other
    errors, in the same shape as `getEciPerson`;
  - re-export the new types.
- **`web/src/types/eci-files.ts`** (WEB is the only editor). Hand-write the §2.4 shapes, narrowed:
  - `EciStage = "before" | "draft" | "final" | "appeals_filed" | "appeals_pending" | "restored"`;
  - `EciRegionKind = "state" | "ut"`;
  - `EciExercise = "sir" | "special_revision"`;
  - `EciNationalGroup` and `EciNationalMeasure`;
  - the interfaces `EciStageValue`, `EciStateMetric`, `EciStateMetrics`, `EciRegionSummary`,
    `EciNationalFigure`, `EciStatesOverview`, `EciStatePage` and `EciStateCount`;
  - `states: EciStateCount[]` added to `EciTimelineOf`.
- **Codegen.** Once the backend lands, run `npm run codegen` with the API up and keep the narrowed types in
  step, following the header comment's rule.
- **`web/src/components/skeletons.tsx`.** Add `EciNumbersSkeleton`: a hero-stat row, a 9×7 grid of shimmer
  squares at `max-width: 720px`, and a legend bar.
- **`globals.css`** (WEB is the only editor). Add the §3.2 tokens and these classes: `.eci-numbers`
  (view rules), `.eci-tiles`, `.eci-tile`, `.eci-tile[data-band="1".."5"]`, `.eci-tile--nomeasure`,
  `.eci-tile--other`, `.eci-tile--empty`, `.eci-tile-code`, `.eci-tile-value`, `.eci-tile-sub`,
  `.eci-col-stage`, `.eci-stage-row`, `.eci-picker` and `.eci-caveat`.
  - Breakpoints are 480px (values hidden and table by default below it) and 640px (the tile sub-line shown
    at and above it).
  - Hover transforms go only inside `@media (hover: hover)`, and motion only inside
    `prefers-reduced-motion: no-preference`, as the existing ECI rules do.

### 3.9 Mobile summary

| width | tiles (when shown) | default view | stage chart |
| --- | --- | --- | --- |
| < 480px | about 33px squares, code only | **table** (tiles one tap away) | stacked rows |
| 480–639px | about 50px, code and value | tiles | stacked under 560px |
| ≥ 640px | up to 76px, code, value and sub-line | tiles | three-column rows |

Pages must work at 360px with a 16px side gutter and no horizontal page scroll. The table scrolls inside
its own wrapper.

### 3.10 Accessibility checklist

- Every tile is a focusable link with a full `aria-label` (§3.4), and the grid is one tab stop with arrow
  keys inside it.
- Colour is never the only signal. Values are printed on the tiles at 480px and up, the legend has band
  labels, and the table is always one tap away and is the default on small screens.
- The metric switch and view toggle are links with `aria-current`, and they work without JS.
- The state picker is a native labelled `<select>` with a submit button, and it works without JS.
- The chart SVGs are `aria-hidden`. Every value is also in HTML text and in the table.
- The drawer behaves as in phase 2, with focus on open and Esc to close.

---

## 4. Work split and hotspots

The two workers run in parallel. The contract between them is this spec: §2.4 shapes and §2.7 values.

**BACKEND worker owns:**

- `data/eci_files/regions.json` (new), `data/eci_files/national.json` (new), and `data/eci_files/states.json`
  (the §1.2 edits only);
- `backend/database/migrations/versions/0007_eci_files_states.py` (new);
- `ingestion/neta_ingest/pipelines/curated/eci_files.py`;
- `ingestion/tests/test_eci_files.py` and `ingestion/tests/fixtures/eci_files/**`;
- `api/neta_api/schemas.py` (**sole editor**), `api/neta_api/services/eci_files.py` and
  `api/neta_api/routers/eci_files.py`;
- `api/tests/test_eci_state_metrics.py` (new), plus `api/tests/__init__.py` if one is needed;
- `.github/workflows/ci.yml` (the api pytest step only);
- `docs/eci-files/openapi.json` and `docs/OPERATIONS.md` (the ECI Files section).

**WEB worker owns:**

- `web/src/app/eci-files/numbers/page.tsx` and `web/src/app/eci-files/numbers/[state]/page.tsx` (new);
- `web/src/app/eci-files/page.tsx` and `web/src/app/eci-files/timeline/page.tsx`;
- `web/src/components/eci-files/`: `StateTileGrid`, `StateTileLegend`, `StateTable`, `StatePicker`,
  `NationalSummary`, `StageChart`, `AfterFinalFigures`, `StateNotes`, `StateMetricTiles`, `DraftCaveat` and
  `HowWeCounted` (all new);
- edits to `QuestionCards.tsx`, `Filters.tsx`, `EntryDetail.tsx` and `CitationList.tsx` (export
  `TIER_LABEL`);
- `web/src/lib/eci-numbers.ts` (new) and `web/src/lib/eci-files.ts`;
- `web/src/lib/api.ts` (**sole editor**), `web/src/types/eci-files.ts` (**sole editor**) and
  `web/src/types/api.ts` (codegen only);
- `web/src/app/globals.css` (**sole editor**) and `web/src/components/skeletons.tsx`.

Neither worker touches `sitemap.ts`, `SiteHeader`, the homepage or `robots.ts`.

**Commits.** Each worker makes one commit covering its code and the docs for it. The spec-to-code pairing
is this file.

---

## 5. Acceptance checks

**Backend**

- [ ] `uv run alembic -c backend/database/alembic.ini upgrade head` reaches `eci_files_states_0006`, then
      `downgrade -1` and `upgrade head` again both succeed, and `alembic check` is clean.
- [ ] `uv run neta eci-files` loads with no errors and prints 36 regions and 14 national figures.
      Re-running it gives identical row counts.
- [ ] `SELECT count(*) FROM eci_file_region` = 36; `eci_file_state` = 36; `SELECT count(DISTINCT
      region_slug) FROM eci_file_state_stage` = 22.
- [ ] `SELECT DISTINCT unnest(states) FROM eci_file_entry` returns only `eci_file_region.name` values, and
      neither "NCT of Delhi" nor "Andaman & Nicobar" appears.
- [ ] Every §2.7 value matches, checked with `curl` against a local API.
- [ ] `uv run pytest` passes for ingestion and api, `uv run ruff check …` passes for all layers, and the
      `api/requirements.txt` check passes.

**Web**

- [ ] `npm run lint`, `npm run typecheck` and `npm run build` pass, and the build runs with the API down.
- [ ] `/eci-files/numbers` shows 36 tiles in the §1.1 layout, with no overlaps and none missing.
      Delhi (32.8%) is in band 5, Lakshadweep (2.5%) in band 1 and Uttar Pradesh (18.7%) in band 4. The
      Andaman & Nicobar tile shows `20.6%*`, Assam is hatched and reads "SR", and Haryana is dashed-empty.
- [ ] `?metric=net_change`: West Bengal shows `−15.9%` in band 5, Kerala `−2.9%` in band 1, and Karnataka
      is no-measure with "no final roll yet".
- [ ] `?metric=appeals`: only West Bengal is coloured (5.9%, band 4). The how-we-counted text says no
      appeals figure is not the same as no appeals.
- [ ] `?view=table` shows a table with no totals row and a final "No figures yet in the record: …" row.
      At 400px width with no `view` param, the table shows and the tiles do not.
- [ ] Keyboard alone works: Tab into the grid, move with the arrows (Bihar → right → Sikkim, Bihar → down
      → West Bengal), and press Enter to open the state page.
- [ ] Submitting the picker, even with JS disabled, lands on `/eci-files/numbers/{slug}`.
- [ ] `/eci-files/numbers/west-bengal` shows three bars on a zero-based scale with the deltas "− 58.21 lakh
      not carried into the draft (7.6%)" and "− 63.64 lakh between draft and final". The "After the final
      roll" section shows three rows. The notes include the adjudication text, the source links open the
      drawer on the same page, and the lane timeline lists the West Bengal entries.
- [ ] `/eci-files/numbers/andaman-and-nicobar-islands` shows the draft bar hatched with a "computed" tag,
      and "Final roll — not in the record yet".
- [ ] `/eci-files/numbers/goa` has no "Restored" row, and its notes begin with the net-deletion note and
      contain "Separately: 97 electors…".
- [ ] `/eci-files/numbers/haryana` shows the no-figures subtitle with "It is in Phase III", the Deccan Herald
      note with a working entry link, and its entries timeline.
- [ ] `/eci-files/numbers/narnia` returns 404.
- [ ] The front page shows the "What happened in my state?" card with the picker, and the timeline has a
      State/UT filter that keeps the window.
- [ ] Toggling the theme leaves every tile's text readable. No new file under `web/src/components/eci-files`
      or `web/src/app/eci-files/numbers` contains a hex colour; check with
      `grep -rnE "#[0-9a-fA-F]{3,6}\b"`.
- [ ] Both new pages send `noindex,nofollow`, and neither appears in `sitemap.ts`, `SiteHeader` or the
      homepage.
- [ ] No verdict words appear in the new copy. "Left off", "not carried into", "net change" and "fall" are
      the only change words used.

---

## Open questions for the owner

1. **Phase III states with only a newspaper's left-off count (Telangana, Andhra Pradesh, Jharkhand,
   Haryana and Punjab) or only a share (Dadra and Nagar Haveli and Daman and Diu, and Arunachal Pradesh).**
   - (a) Keep them as "no figures yet" tiles, with the count in the state-page note. *This is how the spec
     builds them.*
   - (b) Add a `left_off` stage type, so their tiles show a count but no colour, since there is no pre-SIR
     base to divide by.
   - (c) Commission a research pass to open the seven CEO press notes and record real before and draft
     figures.
   - **Recommendation: (c), with (a) in the meantime.** Option (b) puts a newspaper's aggregate on the same
     footing as a stage figure.
2. **Appeals as a tile measure when only West Bengal has a figure.**
   - (a) Keep it as the third measure, with the copy "no appeals figure is not the same as no appeals".
     *This is how the spec builds it, following your brief.*
   - (b) Drop it from the switcher and show appeals only on state pages.
   - **Recommendation: (b).** A grid of 35 "no appeals figure" tiles invites the zero reading that "missing
     ≠ zero" exists to prevent. The change is one line removed from `ECI_METRICS`.
3. **Goa's `restored: 97` stage.** Its own note says 97 is the number left off the final roll, not a
   restored count.
   - (a) Move it into Goa's notes. *This is how the spec builds it.*
   - (b) Add a new stage type, such as `eligible_left_off_final`.
   - (c) Keep it as `restored`.
   - **Recommendation: (a).** Option (c) would publish a bar that says something the record does not, and
     (b) creates a stage type for one state.
4. **Default view on phones.**
   - (a) Table by default under 480px, with tiles one tap away. *This is how the spec builds it.*
   - (b) Tiles always by default, with codes only on phones.
   - **Recommendation: (a).** At 33px a tile can't carry its value, so on a phone the tiles alone mostly
     show colour.
