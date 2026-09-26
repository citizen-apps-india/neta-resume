# ECI Files — phase 5 spec: the fourteen, charge and answer, rule changes, courts

This is the build contract for phase 5. It builds on `SPEC.md`, `REDESIGN-SPEC.md`, `PHASE3-SPEC.md` and
`PHASE4-SPEC.md`, and the stance rules in `data/eci_files/research/BRIEF.md` still apply: every line on
screen comes from a sourced entry, claims are attributed, the Commission's answer sits beside every charge,
and our own voice uses no verdict words.

Phase 5 adds four views. Each one answers a question the record can already answer, but the timeline
spreads the answer across dozens of dots:

| route | question it answers | built from |
| --- | --- | --- |
| `/eci-files/objections` | What did the two Election Commissioners object to, and what happened next? | `data/eci_files/objections.json` |
| `/eci-files/answers` | What was charged, what was the answer, and what does the record show? | `data/eci_files/pairs.json` (new) |
| `/eci-files/rules` and `/eci-files/rules/[diff]` | Which rules changed, and what exactly did the wording say before and after? | `kind: "rule"` entries and `data/eci_files/rule_diffs.json` (new) |
| `/eci-files/courts` and `/eci-files/courts/[case]` | Where does each court case stand, order by order? | the five `kind: "case"` entries in the courts area and `data/eci_files/case_orders.json` (new) |

The design bar: Supreme Court Observer case pages, GitHub split diffs and Federal Register redlines, and
Washington Post investigations. That means a clear hierarchy, the summary before the detail, and every
claim one tap from its source.

## 0. Decisions inherited, and what this phase depends on

- **Launch gate.** The launch gate still holds. Every new page exports `robots: {index: false, follow: false}`, stays out of `sitemap.ts`, and is not linked from `SiteHeader` or the homepage. Pages link to each other, and the ECI front page links to them (§6.1).
- **Charts.** Charts are hand-built SVG in the style of `components/eci-files/DensityStrip.tsx` and `LaneTimeline.tsx`. Do not model them on `components/resume/charts.tsx`, which is Recharts. No new chart library.
- **Tokens.** Components use tokens only. No hex outside `globals.css`.
- **Drawer.** Every entry link on the new pages opens the existing drawer through `?entry=<id>`. The page stays where it is.
- **Phase 3 and phase 4 land first.** Phase 5 needs these from them:
  - **Migration chain.** Phase 3 adds `0007_eci_files_states.py` (revision `eci_files_states_0006`) and phase 4 adds `0008_eci_files_people.py` (revision `eci_files_people_0007`). Phase 5's revision sits on top of phase 4's.
  - **From phase 4:**
    - `EciPhoto`, `EciEntryRef` and the `eci_file_person_media` table;
    - `PersonAvatar({name, photo, size, decorative})` and `initials()`;
    - `eciEntryHref(id, preserve, basePath)` and the `basePath` prop on `EntryDetail`.

    Phase 5 reuses all of these and must not redefine any of them.
  - **From phase 3:** `api/tests/` with pytest in CI.
  - **If phase 4 hasn't merged when phase 5 starts,** branch from phase 4's branch. Say so in the PR description.

## 1. The data files

Four curated files feed this phase. Three are new, written for this phase from the entries. All four are
reviewed data, loaded by full replace, like `headline.json` and `states.json`.

### 1.1 `data/eci_files/objections.json` (exists; two keys added)

The file holds 11 objections (`n` 1–11, numbered by date in this record) and `"missing": 3`. Each objection
has `date`, `date_precision`, `by` (names), `concerns`, `entry_ids`, `followed_by` (text or null) and
`public`. This phase adds two top-level keys:

- `"report_entry_id": "sir-rules-ie-14-objections-report"`, the Indian Express investigation of 23 Sep 2026;
- `"response_entry_id": "sir-rules-eci-pn-119-response"`, the Commission's press note ECI/PN/119/2026 of the same day. It says differing views among members are normal deliberation and that all its decisions over the past year, including the SIR, were unanimous.

`followed_by` sometimes names an entry id in parentheses, for example `(sir-rules-form6-online-sir-declaration)`,
and sometimes names another objection, for example `(objection 10)`. The loader validates the ids (§3) and
the web turns both into links (§6.2). The text is not edited.

### 1.2 `data/eci_files/pairs.json` (new)

```json
{
  "about": "...", "built_on": "2026-09-25",
  "pairs": [
    {"charge_id": "<entry id>",
     "also_recorded_as": ["<entry id>", "..."],
     "response_ids": ["<entry id>", "..."],
     "record_ids": ["<entry id>", "..."],
     "related": [{"id": "<entry id>", "why": "one neutral line"}],
     "note": "one to three neutral sentences, or null"}
  ],
  "unpaired_responses": [{"response_id": "<entry id>", "note": "..."}]
}
```

What each field means, and how the file was built:

- **`charge_id`** is one row on the answers page. A row is either a `status: "claim"` entry or any entry that a response answers. Response links pointing at dropped ids were first resolved through `merges.json`.
  - Some rows are not charges by a person. They are Commission actions, court steps or news reports that a response answers. Examples: the Mamata Banerjee campaign ban, the West Bengal suspension order, the Supreme Court's 17C notice, the bench's question on the speed of Goel's appointment, the May 2026 hearing, the report of Sandhu's Delhi SIR notice, and the Form 6 report.
  - This is why the page's first column is headed "What was said or done", not "Charge".
- **`response_ids`** are `status: "response"` entries only. Most come from `response_to`. Three rows add a response the entry text ties to the charge but that has no `response_to`. Each says so in its `note`:
  - `officials-maharashtra-ceo-june-2025`;
  - `officials-delhi-ceo-notices`;
  - `statements-reporting-cec-press-conference-affidavit-or-apology` on the machine-readable-rolls demand.
- **`record_ids`** are `status: "documented"` entries that bear directly on the point, and only those. Reported entries never go here. 14 rows have one, and each has a `note` saying how it bears, in neutral words. Examples:
  - Kharge's turnout letter → the Commission's own phase 1–2 final turnout release;
  - the dissent notes on the CEC selection → the Anoop Baranwal judgment and Section 7 of the 2023 Act;
  - the Form 6 report → the SIR orders' Declaration Form.
- **`related`** holds linked entries that are not answers. Each carries a `why`:
  - what followed, such as the presiding officers refusing the removal notices;
  - the objection notes on Form 6;
  - on eight reaction statements from 23–25 Sep 2026, the Commission's standing reply (PN/119), labelled as not answering that statement directly.
- **`also_recorded_as`** lists entries that record the same charge in another area. They show under the row, not as rows of their own. Seven groups exist; merges.json should arguably have merged them, which is open question 2.
- **`unpaired_responses`** holds one entry. `elections-2019-2024-mh-portal-mismatch-response` answers an online portal's report that is not in the record.

Counts against today's data: **61 rows, 27 with no response on record, 14 with a record column, and 1
unpaired response.** Every `status: "response"` entry appears exactly once, either in a row or as unpaired.

### 1.3 `data/eci_files/rule_diffs.json` (new)

```json
{
  "about": "...", "built_on": "2026-09-25",
  "text_statuses": ["verbatim", "quoted in reporting", "paraphrased from reporting"],
  "diffs": [
    {"id": "rule-93-inspection",                 // slug, ^[a-z0-9-]+$, the URL segment
     "rule_entry_id": "<kind=rule entry>",
     "title": "...", "document": "...",
     "before_label": "...", "after_label": "...",
     "before": ["line", "..."], "after": ["line", "..."],
     "before_status": "verbatim", "after_status": "verbatim",
     "text_status": "verbatim",                  // the weaker of the two sides
     "excerpt": true,                            // lines outside the change are left out
     "quoted_lines_before": [0], "quoted_lines_after": [1, 2, 3],   // optional, 0-based
     "source_urls": ["..."], "note": "...", "related_entry_ids": ["..."]}
  ],
  "gaps": [{"rule_entry_id": "...", "have": "...", "missing": "...", "why": "..."}]
}
```

**Text statuses.** The task set two statuses; the research needed a third, and that is open question 4.

- **`verbatim`** means copied from the document itself, or from an unaltered reproduction named in `note`.
- **`quoted in reporting`** means the exact wording as a news report quotes it; the document itself was not seen.
- **`paraphrased from reporting`** means a report's description, not the document's wording.
- **Mixed sides.** `quoted_lines_*` flag the quoted lines on a side that mixes quotation and paraphrase.
- **No reconstruction.** Nothing in the file is reconstructed wording.

**The seven diffs:**

| id | rule entry | status | what changes |
| --- | --- | --- | --- |
| `rule-93-inspection` | `elections-2019-2024-rule93-amendment` | verbatim | Rule 93(2)(a) gains "as specified in these rules". The before text is Indian Kanoon's copy of the 1961 Rules; the after text applies the Gazette's amending words (S.O. 5517(E)). The Hindi text places the phrase differently; `note` says so. |
| `selection-committee` | `selection-law-rule-selection-committee` | verbatim | The Anoop Baranwal direction I (PM, LoP, CJI) → Section 7 (PM, LoP, a Cabinet Minister nominated by the PM). The after text is clause 7 of the bill as introduced; the government's list of amendments leaves it untouched. |
| `business-rule` | `selection-law-rule-section-18-business` | verbatim | 1991 Act s.10 → 2023 Act s.18: sub-sections (2) and (3) merge, and the words barely change. The Act text comes from the bill, as above. |
| `sir-document-list-phase-2` | `sir-rules-phase2-forms-last-sir-linkage` | verbatim | Bihar's 11-document list (24 Jun 2025, scanned, read against the page image) → the phase 2 list of 13, adding Aadhaar and an extract of the Bihar SIR roll. |
| `aadhaar-12th-document` | `sir-rules-aadhaar-12th-document` | verbatim | The Bihar list plus paras 3(a)–(b) of the 9 Sep 2025 letter, read from the phase 2 order's Annexure II. |
| `sir-declaration-form-phase-2` | `sir-rules-phase2-forms-last-sir-linkage` | verbatim | Bihar Annexure D (birth-date tiers) → phase 2 Annexure IV (a last-SIR roll lookup and a BLO undertaking). |
| `form-6-online-last-sir` | `sir-rules-form6-online-sir-declaration` | before: paraphrased from reporting; after: quoted in reporting | The three option lines are the portal's wording as The Indian Express quoted it. The statutory Form 6 and the online form could not be fetched. |

**Launch checks.** Two diffs need a check before launch: the Act text for `selection-committee` and
`business-rule` (open question 5). The `gaps` list covers four more rule changes that have only one side,
or none: the BLA criteria (after text verbatim, before text not found), CCTV retention, the Form 6
primaries, and the phase 3 forms.

### 1.4 `data/eci_files/case_orders.json` (new)

```json
{
  "about": "...", "built_on": "2026-09-25",
  "roles": ["order", "judgment", "hearing", "filing", "listing", "recusal", "compliance", "related"],
  "cases": [
    {"slug": "bihar-sir", "short_name": "Bihar SIR", "case_entry_id": "courts-case-bihar-sir",
     "court": "Supreme Court of India", "short_status": "pending | disposed | referred",
     "status_note": "Judgment 27 May 2026 (2026 INSC 564).",
     "parties": {"petitioners": ["..."], "respondents": ["..."]},
     "items": [{"entry_id": "...", "role": "order", "note": "optional"}]}
  ],
  "unmapped": [{"entry_id": "...", "why": "..."}]
}
```

- **How the file was built.** It comes from each case entry's `notes`, which list the order entries already recorded in other areas. The five courts-area case entries point to their orders that way, not through a `case_id` in `details`. So a curated mapping is the only reliable link, and the loader does not guess from case numbers.
- **What each case holds:**

  | slug | items | status |
  | --- | --- | --- |
  | `form-17c` | 3 | pending |
  | `evm-vvpat` | 5 | disposed |
  | `2023-act-challenge` | 20 | referred |
  | `bihar-sir` | 10 | disposed |
  | `west-bengal-sir` | 13 | pending |

- **Roles.** `compliance` is a Commission act that carries out an order, such as the 9 Sep 2025 Aadhaar letter. `related` is linked but not part of the proceedings: the order under challenge, an earlier separate case, or a parallel petition. Each `related` item has a `note`.
- **Unmapped.** Two court-facing entries stay unmapped because the record does not say which petition they were filed in.
- **Invariant.** An entry belongs to at most one case.

## 2. Storage: Alembic revision `eci_files_views_0008`

- **File:** `backend/database/migrations/versions/0009_eci_files_views.py`
- **Revision id:** `eci_files_views_0008`
- **`down_revision`:** `"eci_files_people_0007"`. Read it from `0008_eci_files_people.py` before writing. If phase 4 renamed it, use its name.

Every `entry_id` column references `eci_file_entry(id) ON DELETE CASCADE`. Every table is fully replaced on
each load.

```
eci_file_objection
  n               smallint PRIMARY KEY CHECK (n > 0)
  date            date
  date_precision  text NOT NULL CHECK (date_precision IN ('day','month','year'))
  concerns        text NOT NULL
  followed_by     text
  public          boolean NOT NULL DEFAULT false

eci_file_objection_person
  n               smallint NOT NULL REFERENCES eci_file_objection(n) ON DELETE CASCADE
  person_slug     text NOT NULL REFERENCES eci_file_person(slug) ON DELETE CASCADE
  position        smallint NOT NULL
  PRIMARY KEY (n, person_slug)

eci_file_objection_entry
  n               smallint NOT NULL REFERENCES eci_file_objection(n) ON DELETE CASCADE
  entry_id        text NOT NULL REFERENCES eci_file_entry(id) ON DELETE CASCADE
  position        smallint NOT NULL
  PRIMARY KEY (n, entry_id)
  INDEX (entry_id)

eci_file_objection_meta                                   -- one row
  id              smallint PRIMARY KEY CHECK (id = 1)
  missing         smallint NOT NULL CHECK (missing >= 0)
  notes           text
  report_entry_id   text REFERENCES eci_file_entry(id) ON DELETE SET NULL
  response_entry_id text REFERENCES eci_file_entry(id) ON DELETE SET NULL

eci_file_pair
  charge_id       text PRIMARY KEY REFERENCES eci_file_entry(id) ON DELETE CASCADE
  position        smallint NOT NULL UNIQUE
  note            text

eci_file_pair_item
  charge_id       text NOT NULL REFERENCES eci_file_pair(charge_id) ON DELETE CASCADE
  entry_id        text NOT NULL REFERENCES eci_file_entry(id) ON DELETE CASCADE
  role            text NOT NULL CHECK (role IN ('response','record','related','same'))
  position        smallint NOT NULL
  why             text                                    -- related only
  PRIMARY KEY (charge_id, entry_id, role)
  INDEX (entry_id)

eci_file_unpaired_response
  response_entry_id text PRIMARY KEY REFERENCES eci_file_entry(id) ON DELETE CASCADE
  note            text

eci_file_rule_diff
  id              text PRIMARY KEY CHECK (id ~ '^[a-z0-9-]+$')
  position        smallint NOT NULL UNIQUE
  rule_entry_id   text NOT NULL REFERENCES eci_file_entry(id) ON DELETE CASCADE
  title           text NOT NULL
  document        text NOT NULL
  before_label    text NOT NULL
  after_label     text NOT NULL
  before_lines    text[] NOT NULL
  after_lines     text[] NOT NULL
  before_status   text NOT NULL   -- CHECK IN ('verbatim','quoted in reporting','paraphrased from reporting')
  after_status    text NOT NULL   -- same CHECK
  text_status     text NOT NULL   -- same CHECK
  excerpt         boolean NOT NULL DEFAULT false
  quoted_lines_before smallint[] NOT NULL DEFAULT '{}'
  quoted_lines_after  smallint[] NOT NULL DEFAULT '{}'
  source_urls     text[] NOT NULL CHECK (cardinality(source_urls) >= 1)
  note            text
  INDEX (rule_entry_id)

eci_file_rule_diff_entry                                  -- related_entry_ids
  diff_id         text NOT NULL REFERENCES eci_file_rule_diff(id) ON DELETE CASCADE
  entry_id        text NOT NULL REFERENCES eci_file_entry(id) ON DELETE CASCADE
  PRIMARY KEY (diff_id, entry_id)
  INDEX (entry_id)

eci_file_case
  slug            text PRIMARY KEY CHECK (slug ~ '^[a-z0-9-]+$')
  position        smallint NOT NULL UNIQUE
  short_name      text NOT NULL
  case_entry_id   text NOT NULL UNIQUE REFERENCES eci_file_entry(id) ON DELETE CASCADE
  court           text NOT NULL
  short_status    text NOT NULL CHECK (short_status IN ('pending','disposed','referred'))
  status_note     text
  parties         jsonb NOT NULL DEFAULT '{}'

eci_file_case_item
  case_slug       text NOT NULL REFERENCES eci_file_case(slug) ON DELETE CASCADE
  entry_id        text NOT NULL UNIQUE REFERENCES eci_file_entry(id) ON DELETE CASCADE
  role            text NOT NULL CHECK (role IN ('order','judgment','hearing','filing','listing','recusal','compliance','related'))
  note            text
  PRIMARY KEY (case_slug, entry_id)
```

- **Downgrade** drops the eleven tables, children first.
- **`alembic check`** stays clean.
- **Docs.** Record the tables in the ECI Files section of `docs/OPERATIONS.md`, like phases 3 and 4.

## 3. Loader: `ingestion/neta_ingest/pipelines/curated/eci_files.py`

These are additions to the existing full-replace loader. The pattern is the one `states.json` and
`headline.json` already use.

1. **New default paths.** Add these under `data/eci_files/`:
   - `DEFAULT_OBJECTIONS_PATH` (`objections.json`)
   - `DEFAULT_PAIRS_PATH` (`pairs.json`)
   - `DEFAULT_RULE_DIFFS_PATH` (`rule_diffs.json`)
   - `DEFAULT_CASES_PATH` (`case_orders.json`)
   - `DEFAULT_MERGES_PATH` (`merges.json`)

   They load only when `run()` gets no explicit `path`, or when passed explicitly as keyword args (`objections_path=`, and so on). Tests never read the real files.
2. **Resolving `response_to` through `merges.json`.** Before insert, if an entry's `response_to` is a `drop` id in `merges.json`, rewrite it to that merge's `keep` id.
   - Today this fixes five dangling links, for example `officials-goel-response-97` → `sir-rules-goa-final-roll-97`.
   - Print `[eci-files] resolved N response links through merges.json`.
   - A `response_to` that still points at no loaded entry is a validation error.
3. **Pydantic models.** Add `ObjectionFile`, `PairFile`, `RuleDiffFile` and `CaseFile` with `extra="forbid"` on the inner items, so a typo in a curated field fails loudly. Top-level `about`, `built_on`, `notes` and `gaps` are allowed.
4. **Cross-reference validation.** Collect every error and raise them all at once, with the existing `EciFilesValidationError`. The rules:
   - Every referenced id exists among the loaded, non-excluded entries.
   - **Objections:**
     - `n` values are unique and contiguous from 1.
     - Every `by` name slugifies to a person that exists after the person upsert.
     - `entry_ids` is non-empty.
     - In `followed_by`, every parenthesised token that starts with a known area prefix is a loaded entry id. The known prefixes are `commissioners-`, `courts-`, `elections-2019-2024-`, `numbers-`, `officials-`, `selection-law-`, `sir-rules-` and `statements-reporting-`.
     - The `(objection N)` tokens have `N` ≤ the highest `n`.
   - **Pairs:**
     - `charge_id` is unique.
     - No id is both a `charge_id` and in another pair's `also_recorded_as`.
     - Every `response_ids` entry has status `response`.
     - Every `record_ids` entry has status `documented`.
     - Every `related` item has a non-empty `why`.
     - `unpaired_responses` ids have status `response` and appear in no pair.
   - **Rule diffs:**
     - The `rule_entry_id` entry has kind `rule`.
     - `id` matches `^[a-z0-9-]+$` and is unique.
     - `before` and `after` are non-empty.
     - `text_status` equals the weaker of `before_status` and `after_status`, ranked verbatim > quoted in reporting > paraphrased from reporting.
     - `quoted_lines_*` indexes are in range.
     - `source_urls` is non-empty.
   - **Cases:**
     - The `case_entry_id` entry has kind `case`.
     - Every role is in `roles`.
     - No entry is an item of two cases, and a case entry is not its own item.
5. **Replace order.** Inside the same `session_scope()`, delete the phase 5 tables first, children before parents, then the existing tables. Insert the phase 5 rows after entries and persons.
   - `eci_file_pair_item` rows get `role='same'` for `also_recorded_as`, `'response'`, `'record'` and `'related'`, with `position` preserving file order within each role.
6. **Summary line.** Print one line: `[eci-files] loaded 11 objections (3 missing), 61 pairs (27 without a response), 7 rule diffs, 5 cases (51 items)`.

**Tests.** They go in `ingestion/tests/test_eci_files.py`, with fixtures under `ingestion/tests/fixtures/eci_files/extra/`, and small files that reference fixture entry ids.

- **Validation (one test each).**
  - an unknown id in each file;
  - a record id that isn't documented;
  - a response id that isn't a response;
  - a `text_status` that doesn't match its sides;
  - a duplicate case item;
  - an objection `n` gap;
  - a `followed_by` token for a missing entry.
- **Response resolution.** A `response_to` pointing at a dropped id is rewritten to the kept id.
- **Postgres** (skipped without `NETA_TEST_DATABASE_URL`):
  - loading the fixture twice leaves the same row counts in all eleven tables;
  - deleting an entry from the fixture and reloading removes its pair, case and diff rows.

## 4. API

The API files are `api/neta_api/services/eci_files.py`, `routers/eci_files.py` and `schemas.py`, and the
backend worker is the sole editor of `schemas.py`. Use the same cache headers as the other read routes.
Every list is small, so each route loads its whole set in a handful of queries and assembles it in Python,
like the existing service.

### 4.1 Shared shapes (`schemas.py`)

```python
class EciEntryRef(BaseModel):              # phase 4's; add one optional field
    id: str; title: str; date: _Date | None = None; date_precision: str; status: str
    check_status: str | None = None        # NEW, optional so phase 4 callers are unaffected

class EciEntryCard(BaseModel):             # enough for a row or cell; the drawer fetches the full entry
    id: str; kind: str; date: _Date | None = None; date_precision: str
    title: str; summary: str; status: str; lane: str
    attributed_to: str | None = None; check_status: str
    people: list[EciPersonRef] = []
    citation_count: int
    lead_citation: EciCitation | None = None   # position 1

class EciPersonWithPhoto(BaseModel):
    slug: str; name: str; photo: EciPhoto | None = None     # LEFT JOIN eci_file_person_media (phase 4)
```

- **The card loader.** Add `_load_cards(db, ids) -> list[dict]` next to `_load_entries`. It makes three queries: base columns, people, and a citation count with a lateral lead citation. Every new route builds its cells with it.

### 4.2 `GET /eci-files/objections` → `EciObjectionsPage`

```python
class EciObjection(BaseModel):
    n: int; date: _Date | None = None; date_precision: str
    by: list[EciPersonWithPhoto]
    concerns: str; followed_by: str | None = None
    followed_by_refs: list[EciEntryRef] = []     # entries named "(id)" inside followed_by, in text order
    public: bool
    entries: list[EciEntryRef]

class EciObjectionPersonCount(BaseModel):
    slug: str; name: str; photo: EciPhoto | None = None
    count: int; joint: int                       # joint = objections signed with someone else

class EciObjectionsPage(BaseModel):
    identified: int; missing: int; reported_total: int      # reported_total = identified + missing
    notes: str | None = None
    report: EciEntryRef | None = None
    response: EciEntryCard | None = None
    objections: list[EciObjection]               # n ascending
    by_person: list[EciObjectionPersonCount]     # count desc, then name
```

Expected values today:

- `identified` 11, `missing` 3, `reported_total` 14;
- `by_person`: Sandhu, count 8 and joint 2; Joshi, count 5 and joint 2;
- `response.id` is `sir-rules-eci-pn-119-response`.

### 4.3 `GET /eci-files/answers?view=all|no-response|with-record` → `EciAnswersPage`

```python
class EciRelatedRef(BaseModel):
    entry: EciEntryRef; why: str

class EciAnswerRow(BaseModel):
    charge: EciEntryCard
    also_recorded_as: list[EciEntryRef] = []
    responses: list[EciEntryCard] = []           # date ascending
    record: list[EciEntryCard] = []
    related: list[EciRelatedRef] = []
    note: str | None = None
    curated: bool                                # false = synthesised (below)

class EciAnswersCounts(BaseModel):
    rows: int; with_response: int; without_response: int; with_record: int

class EciUnpairedResponse(BaseModel):
    response: EciEntryCard; note: str | None = None

class EciAnswersPage(BaseModel):
    counts: EciAnswersCounts                     # always for view=all
    rows: list[EciAnswerRow]                     # charge date descending, then id
    unpaired_responses: list[EciUnpairedResponse]
```

**Completeness rule.** A new claim can't be missed because nobody updated `pairs.json`.

- **Synthesised rows.** After loading the curated rows, add one synthesised row (`curated: false`) for each of these:
  - every `status='claim'` entry;
  - every entry that a `status='response'` entry's `response_to` points at.

  Skip any entry that is already a `charge_id`, an `also_recorded_as` id, or an unpaired response.
- **What a synthesised row holds.** Its `responses` come from `response_to`. `record`, `related` and `note` are empty.
- **Where the logic lives.** Put it in a pure function, `assemble_answer_rows(pairs, items, claim_ids, response_links, unpaired_ids)`, and test it in `api/tests/test_eci_answers.py` with no database.
- **Expected today.** 61 rows and 0 synthesised: `without_response` 27, `with_record` 14.

### 4.4 `GET /eci-files/rules` and `GET /eci-files/rules/diffs/{id}`

```python
class EciRuleDiffRef(BaseModel):
    id: str; title: str; text_status: str

class EciRuleRow(BaseModel):
    entry: EciEntryCard
    diffs: list[EciRuleDiffRef] = []

class EciRulesPage(BaseModel):
    rules: list[EciRuleRow]                      # every kind='rule' entry, date descending, then id
    diffs: list[EciRuleDiffRef]                  # file order
    counts: dict[str, int]                       # {"rules": 39, "with_diff": 6, "diffs": 7}

class EciRuleDiff(BaseModel):
    id: str; title: str; document: str
    rule_entry: EciEntryCard
    before_label: str; after_label: str
    before: list[str]; after: list[str]
    before_status: str; after_status: str; text_status: str
    excerpt: bool
    quoted_lines_before: list[int] = []; quoted_lines_after: list[int] = []
    source_urls: list[str]; note: str | None = None
    related: list[EciEntryRef] = []
```

- **404.** An unknown id returns 404 `"rule diff not found"`.
- **No diffing in the API.** The API returns lines. The web computes the diff (§6.4), so the logic lives in one place next to its renderer.

### 4.5 `GET /eci-files/courts` and `GET /eci-files/courts/{slug}`

```python
class EciCaseSummary(BaseModel):
    slug: str; short_name: str; title: str       # title = case entry title
    case_number: str | None = None               # details.case_number
    court: str; short_status: str; status_note: str | None = None
    item_count: int; order_count: int            # order_count = roles order|judgment
    first_date: _Date | None = None; last_date: _Date | None = None
    latest: EciEntryRef | None = None            # latest non-related item

class EciCourtsPage(BaseModel):
    cases: list[EciCaseSummary]                  # file order
    other_court_entries: int                     # lane='courts' entries in no case, case entries excluded

class EciCaseItem(BaseModel):
    role: str; note: str | None = None; entry: EciEntryCard

class EciCasePage(BaseModel):
    slug: str; short_name: str; court: str; short_status: str; status_note: str | None = None
    case: EciEntry                               # the full case entry (summary, citations, notes)
    case_name: str                               # details.case_name, else case.title
    case_number: str | None = None; bench: str | None = None; citation: str | None = None
    parties: dict[str, list[str]]                # {"petitioners": [...], "respondents": [...]}
    items: list[EciCaseItem]                     # entry date ascending, then id
```

An unknown slug returns 404 `"case not found"`.

### 4.6 `GET /eci-files/entries/{id}` gains `context`

The route now returns `EciEntryDetail`. Every other route keeps returning `EciEntry`, so timeline payloads
don't grow.

```python
class EciPairContext(BaseModel):
    charge: EciEntryRef
    role: str                                    # charge | response | record | related | same
    responses: list[EciEntryRef] = []
    record: list[EciEntryRef] = []
    note: str | None = None

class EciEntryContext(BaseModel):
    pairs: list[EciPairContext] = []             # every curated pair this entry is part of
    case: dict | None = None                     # {"slug","short_name","role"} if the entry is a case or case item
    objections: list[dict] = []                  # [{"n","concerns"}] for objections citing this entry
    rule_diffs: list[EciRuleDiffRef] = []        # diffs whose rule entry or related entries include it

class EciEntryDetail(EciEntry):
    context: EciEntryContext = EciEntryContext()
```

- **Queries.** One per context kind, each on an indexed `entry_id` column.
- **Synthesised pairs** are not included. The drawer already shows `responses` and `response_to` for those.

### 4.7 OpenAPI and API tests

- **OpenAPI.** Regenerate `docs/eci-files/openapi.json` by dumping `app.openapi()`, as phase 3 does.
- **`api/tests/test_eci_answers.py`.** These are pure tests. They cover:
  - that synthesis adds uncovered claims and response targets;
  - that `also_recorded_as` ids are not synthesised;
  - that the order is date descending;
  - that the counts are computed on `view=all` whatever the filter.

## 5. Copy (neutral, exact)

The web worker uses these strings as written. Any change to them goes through the owner.

- **`/eci-files/objections`**
  - Eyebrow: `ECI FILES · THE FOURTEEN`
  - Title: `The fourteen objections`
  - Lede: `On 23 September 2026 The Indian Express reported that two of the three Election Commissioners, Sukhbir Singh Sandhu and Vivek Joshi, objected on record 14 times in ten months. This record can match 11 of those objections to a dated note or letter. The published reports do not itemise the other three.`
  - Response box heading: `The Commission's response, 23 Sep 2026`
  - Response box body: `response.summary`, then `Attributed to {attributed_to}` and `Read the press note →`, which opens the drawer.
  - Empty slot heading: `Not yet public`
  - Empty slot body, shown once, on the first empty slot: `The Indian Express reported 14 objections. Its published reports describe 11 that this record can match to a dated note or letter.`
  - `public: false` label: `Not a public document · described in reporting`
  - Numbering note: `Numbered by date in this record, not by the newspaper.`
- **`/eci-files/answers`**
  - Eyebrow: `ECI FILES · CHARGE AND ANSWER`
  - Title: `Charge and answer`
  - Lede: `Each row sets what was said or done beside the response to it. A third column appears only where a primary document in the record bears directly on the point. Where no response is recorded, the row says so.`
  - Column headings: `What was said or done` · `The response` · `What the record shows`
  - Empty response cell: `No response on record.`
  - View chips: `All {rows}` · `No response on record {without_response}` · `With a document {with_record}`
- **`/eci-files/rules`**
  - Eyebrow: `ECI FILES · RULE CHANGES`
  - Title: `Rule changes`
  - Lede: `Every rule, form and order change in the record. Where the wording before and after could be sourced, it is set out line by line, with a label saying whether it comes from the document itself or from news reports.`
- **Text status labels**
  - `verbatim` → `Verbatim from the document`
  - `quoted in reporting` → `Wording as quoted in news reports`
  - `paraphrased from reporting` → `Paraphrased from news reports: not the document's wording`
- **Banner when `text_status` isn't verbatim**
  - Paraphrase: `This comparison is built from news reports, not from the documents. The lines describe the change; they do not reproduce it.`
  - If only quoted: `The wording is as quoted in news reports. The document itself could not be opened.`
- **`/eci-files/courts`**
  - Eyebrow: `ECI FILES · COURTS`
  - Title: `The court cases`
  - Lede: `Five cases about the Commission's work, each with its parties, bench and status, and every recorded step in date order.`
- **Status chips (text, not colour)**
  - `pending` → `Pending`
  - `disposed` → `Decided`
  - `referred` → `Pending · referred to the Chief Justice`
- **Role chips**
  - `order` → `Order`
  - `judgment` → `Judgment`
  - `hearing` → `Hearing`
  - `filing` → `Filing`
  - `listing` → `Listing`
  - `recusal` → `Recusal`
  - `compliance` → `Commission acts on order`
  - `related` → `Related`

## 6. Website

### 6.1 Shared pieces

- **Drawer.** Each new page accepts `?entry=`. Move the timeline page's `EntryDrawerBody` into `components/eci-files/DrawerFromParam.tsx` (server), with props `{id, basePath, preserve}`. It fetches `getEciEntry(id)` and renders `<EntryDrawer><EntryDetail entry basePath preserve/></EntryDrawer>`. Use it on the timeline page too.
- **Entry links.** `EntryRefLink({entry, basePath, preserve, showStatus})` renders the date (precision-aware, `formatEciDate`), the title, an optional small `StatusChip`, and a `PendingFlag` when `check_status === "unchecked"`. Its href is `eciEntryHref(id, preserve, basePath)`. Use it for every entry mention on the new pages.
- **`EntryDetail` gains a context block.** It renders `entry.context` when present. On a plain `EciEntry` it renders nothing, so phase 3 and 4 callers are unchanged. It has three parts:
  - **Charge and answer.** One small box per pair: `Charge`, then the charge link (or `This entry` when role is `charge`), then `Responses` (links, or `No response on record.`), then `What the record shows` (links, when any), then the note. It ends with `See all charges and answers →`, linking to `/eci-files/answers#charge-{charge.id}`.
  - **Case.** `Part of the case: {short_name} →`, linking to `/eci-files/courts/{slug}` and showing the role chip.
  - **Objections and diffs.** `Objection {n} of 14 →`, linking to `/eci-files/objections#objection-{n}`. `Before and after: {title}`, with its text-status label, linking to `/eci-files/rules/{id}`.
- **Front page.** In `QuestionCards.tsx`, add four cards after phase 3's card:
  - `What did two Commissioners object to?` → `/eci-files/objections`
  - `What was charged, and what was the answer?` → `/eci-files/answers`
  - `Which rules changed, word for word?` → `/eci-files/rules`
  - `Where do the court cases stand?` → `/eci-files/courts`
- **Footer links.** Each new page ends with a footer link row to the other three, plus `← ECI Files`.
- **Failure copy.** When the API fails, every page shows the existing `The record hasn't loaded — try again in a moment.` The build must not need the API, so there is no `generateStaticParams`. The dynamic pages call `notFound()` on a 404.

### 6.2 `/eci-files/objections` (`app/eci-files/objections/page.tsx`)

The page reads top to bottom: summary first, then pattern, then detail.

1. **`SectionHero`.** The §5 eyebrow, title and lede, with the numbering note in `--muted`.
2. **The response box.** A bordered box with `--eci-response` as a 3px left rule, holding the §5 response copy. It sits before the ledger so the Commission's answer is read with the charge.
3. **By-person row.** One `PersonAvatar` (phase 4, `decorative`) per `by_person` item, with the name linked to `/eci-files/people/{slug}` and `8 objections · 2 jointly`.
4. **`ObjectionStrip`** (new, server, hand-built SVG in `components/eci-files/ObjectionStrip.tsx`):
   - **Axis.** Months `2025-11` to `2026-09`, from `formatMonthKey`/`monthRange` in `lib/eci-files.ts`. Tick labels are month initials, with the year under January and under the first month. `viewBox` is width 660 and height `24 + 44 × rows`; it scales to its container.
   - **Rows.** One per `by_person` item, in the same order. The row label (surname) sits at the left, and the count sits at the right.
   - **Marks.**
     - **Day precision.** A 9px dot filled `--eci-ink`, at the date's fraction of the axis.
     - **Month precision.** A 9px ring at mid-month, stroked `--eci-ink` with a `3 2` dash. The legend reads `Month known, day not`.
     - **Joint objections** (`by.length > 1`) get a dot in each row, joined by a 1.5px vertical line in `--ink2`. The legend reads `Joint note`.
   - **Report marker.** A thin dashed vertical line in `--rule` at 23 Sep 2026, labelled `Report and response` in 10px `--muted`.
   - **Links.** Each mark is an `<a href="#objection-{n}">` with `aria-label="Objection {n}, {date}, {names}"` and a `:focus-visible` ring. Objections 2 and 3 fall on the same day in the same row, so offset marks that share a day by ±5px vertically.
   - **Accessibility.** Wrap it in `<figure>` with `<figcaption>Objections by commissioner, November 2025 to September 2026</figcaption>`. The svg has `role="img"` and an `aria-label` summarising the counts. The ledger below is the data table equivalent, so say so in a visually hidden sentence.
5. **The ledger** (`ObjectionLedger.tsx`, an `<ol class="eci-ledger">` with 14 `<li>`):
   - **Filled slot** (`id="objection-{n}"`, `.eci-slot`). The layout is a 2-column grid: a 120px meta column and a body.
     - **Meta column.** `No. {n}` in mono, the date (precision-aware), then `PersonAvatar` × `by`, 28px, with the names.
     - **Body.**
       - `h3`: `concerns` (a full sentence; there is no separate title).
       - `What followed`, a mono 10px label, then `followed_by`. It is rendered by `linkifyFollowedBy(text, refs)` in `lib/eci-files.ts`, a pure function that returns segments. `(entry-id)` becomes a `(see entry)` drawer link and `(objection N)` becomes `(objection N)` linked to `#objection-N`. A null `followed_by` renders `Nothing further in the record.`
       - `Entries`: one `EntryRefLink` per `entries` item.
       - The `public: false` label (§5).
   - **Empty slot** (`.eci-slot-empty`, 3 of them, `aria-label="Objection not yet public"`). The border is dashed `--border2` with no fill. There is no number; the slot shows the §5 heading and, on the first slot only, the body.
6. **Footer links** (§6.1).

### 6.3 `/eci-files/answers` (`app/eci-files/answers/page.tsx`)

1. **`SectionHero`.** The §5 copy.
2. **View chips.** Three links that set `?view=`, with counts from `counts`. Plain links, so they work without JS, and the current chip has `aria-current="page"`.
3. **Column header row.** Visible at ≥ 960px and sticky under the site header (`top: 0` inside `main`). It holds the three §5 column headings.
4. **Rows, grouped by year** of `charge.date`, newest first, with an `h2` per year. Each row is an `<article id="charge-{id}" aria-labelledby>` using `.eci-answer-row`: a 3-column grid at ≥ 960px (`1.1fr 1fr 0.9fr`), stacked below that.
   - **Cell 1 (what was said or done).**
     - date, `StatusChip`, then the `attributed_to` name in bold;
     - the title (an `h3`, linking to the drawer);
     - `summary`, clamped to 4 lines, with `Read in full` opening the drawer;
     - `Also recorded as:` followed by `EntryRefLink`s, when there are any.
   - **Cell 2 (the response).** One block per response: date, `attributed_to`, title (drawer link), and summary clamped to 3 lines. With no response, it shows `No response on record.` in `--muted`. After that come the `related` items, each as `{why}: ` plus an `EntryRefLink`.
   - **Cell 3 (what the record shows).** One block per record entry: `StatusChip` (it will read Document), date and title. An empty record renders nothing: no dash, because a dash would read as missing data rather than "no document bears on this". Below 960px the cell and its heading are omitted when empty.
   - **Note.** When present, it spans all three columns under a mono `Note` label in `--ink2`.
   - **Stacked view.** Each cell starts with its column heading as a mono 10px label. On desktop that label is visually hidden and kept for screen readers.
5. **Unpaired responses.** A last section, `Responses whose charge is not in the record`, lists each response with its note.
6. **Drawer.** Handled by `DrawerFromParam`, with basePath `/eci-files/answers`, preserving `view`.

### 6.4 `/eci-files/rules` and `/eci-files/rules/[diff]`

**Index (`app/eci-files/rules/page.tsx`):**

1. **`SectionHero`.** The §5 copy, then counts: `39 rule changes · 7 before-and-after comparisons`.
2. **"Before and after" strip.** One card per `diffs` item: title, a `TextStatusBadge`, and a link to `/eci-files/rules/{id}`. It is a grid, 2 columns at ≥ 760px.
3. **The full list**, grouped by year, newest first. Each row shows the date, `StatusChip`, title (drawer link), and one line of summary. When `diffs` is non-empty it adds a `Before and after →` link for each, with the badge in its short form: `Verbatim`, `Quoted in reports` or `Paraphrased`.

**Diff page (`app/eci-files/rules/[diff]/page.tsx`):**

1. **Breadcrumb.** `Rule changes` → `/eci-files/rules`. Then the `h1` title, `document` in `--muted`, and `Rule entry:` followed by an `EntryRefLink` (the drawer).
2. **Status.** Show one `TextStatusBadge` when the two sides match. Otherwise show a badge above each column. Show the §5 banner when `text_status !== "verbatim"`. When `excerpt` is true, add `Excerpt: lines outside the change are left out.`
3. **The diff.**
   - **Computing it.** Use a pure `diffLines(before, after)` in a new `web/src/lib/eci-diff.ts`:
     - Line-level LCS on exact string equality produces the ops `{kind: "same" | "del" | "add", text, a?: number, b?: number}`.
     - Then each run of consecutive `del`s followed by consecutive `add`s is paired index by index. Each pair becomes `{kind: "change", a, b, before: Segment[], after: Segment[]}`, where the segments come from a word-level LCS over `text.split(/(\s+)/)`.
     - Unpaired leftovers stay as `del` or `add`. Keep it under 120 lines with no dependencies.
   - **Split view** (≥ 640px, `.eci-diff-split`). Two columns, headed `before_label` and `after_label`, each with its badge when the sides differ. Rows align by op:
     - `same` lines show on both sides in `--ink2`;
     - `del` goes left and `add` goes right, with an empty cell opposite;
     - a `change` row shows both sides with the changed segments marked.
   - **Line numbers.** Each line gets a 1-based line number in a mono `--faint` gutter.
   - **Unified view** (< 640px, `.eci-diff-unified`). One column with a gutter of `−`, `+` or a space. A `change` becomes a `−` line followed by a `+` line.
   - **Marking** is a Federal Register redline, so colour is never the only cue:
     - removed text is `<del>`, struck through, on `--eci-diff-del-bg` with text `--eci-diff-del-fg`;
     - added text is `<ins>`, underlined with 2px thickness, on `--eci-diff-add-bg` with `--eci-diff-add-fg`;
     - each changed line starts with a visually hidden `Removed:` or `Added:`.
   - **Quoted and paraphrased lines.** A line index in `quoted_lines_*` renders inside “ ” with the class `.eci-diff-quoted`. On a side that is not `verbatim`, every other line renders in italics, so paraphrase never looks like quotation.
   - **Server-rendered.** Both views render on the server and CSS picks one, so no client JS is needed.
4. **Details.** Show `note` under a mono `About this text` label. `Sources` lists `source_urls` as links, with the host shown and the full URL in `title`. Then `Related entries` as `EntryRefLink`s.

**Check the diff logic by hand before merge.** The web has no test runner, so the worker checks these in a
scratch script and records the results in the PR:

- `rule-93-inspection` gives exactly one `change` whose only `ins` segment is `as specified in these rules `;
- `business-rule` gives one `same` line and one `change`, with (2) and (3) merged;
- `sir-document-list-phase-2` shows item 1's added `a ` as an insertion;
- a diff of identical arrays gives all `same`.

### 6.5 `/eci-files/courts` and `/eci-files/courts/[case]`

**Index (`app/eci-files/courts/page.tsx`):**

1. **`SectionHero`.** The §5 copy.
2. **Five `CaseCard`s** (a 2-column grid at ≥ 760px). Each card is one link to `/eci-files/courts/{slug}` and shows:
   - `short_name` (`h2`) and `title` in `--ink2`;
   - `case_number` in mono, which may wrap;
   - `court`;
   - the status chip (§5) and `status_note`;
   - `{item_count} recorded steps · {order_count} orders and judgments`;
   - `Latest: {date} · {title}`.
3. **Other court entries.** `{other_court_entries} other court entries are not grouped into a case.` → `/eci-files/timeline?lane=courts`.

**Case page (`app/eci-files/courts/[case]/page.tsx`).** The model is a Supreme Court Observer case page.

1. **Breadcrumb and title.** Breadcrumb `Courts` → `/eci-files/courts`. Then the `h1` `case_name` and the status chip with `status_note`.
2. **Facts panel.** A `<dl class="eci-case-facts">`, 2 columns at ≥ 760px and 1 below, holding:
   - `Court`, `Case number` (mono), `Bench`, and `Citation` (when present);
   - `Petitioners` and `Respondents` (lists);
   - `Filed or first recorded`, from `case.date` with precision.

   Missing values render `—`.
3. **Summary.** `h2` `In brief`, then `case.summary`, then `Sources:` with `CitationList`, then `Open the full entry →` (the drawer).
4. **Timeline.** `h2` `Every recorded step`. It is an `<ol class="eci-case-timeline">` with a vertical rail in `--rule`, grouped by year with a year label on the rail. Each item shows:
   - the date (mono, precision-aware), the role chip, `StatusChip` and `PendingFlag`;
   - the title (`h3`, drawer link) and a 2-line summary clamp;
   - the item's `note` in `--muted`.

   `related` items render at reduced emphasis: `--muted` text and a hollow rail dot. The last non-related item gets a `Latest` label.
5. **Drawer.** `DrawerFromParam` with basePath `/eci-files/courts/{slug}`.

### 6.6 Types, API client and CSS

- **`web/src/types/eci-files.ts`.** The web worker is the sole editor. Hand-write the §4 shapes now: `EciEntryCard`, `EciPersonWithPhoto`, `EciObjection*`, `EciAnswer*`, `EciRule*`, `EciCase*`, `EciCourtsPage`, `EciEntryContext` and `EciEntryDetail`. Switch to generated types after `npm run codegen`.
- **`web/src/lib/api.ts`.** The web worker is the sole editor. Add:
  - `getEciObjections()` (revalidate 3600);
  - `getEciAnswers(view)` (3600);
  - `getEciRules()` (3600);
  - `getEciRuleDiff(id)` (returns `null` on 404; 3600);
  - `getEciCourts()` (3600);
  - `getEciCase(slug)` (returns `null` on 404; 3600).

  Change `getEciEntry` to return `EciEntryDetail`.
- **`web/src/app/globals.css`.** The web worker is the sole editor.
  - **New tokens.** Add these for both themes, next to the existing `--eci-*` tokens. The diff pair is blue for added and orange for removed, which is safe for colour-blind readers, and it never carries meaning alone (§6.4). Check each tint against its text for 4.5:1.

    | token | light | dark |
    | --- | --- | --- |
    | `--eci-diff-add-bg` | `#E6F0FB` | `#16263A` |
    | `--eci-diff-add-fg` | `#1B5FAE` | `#8DBBF0` |
    | `--eci-diff-del-bg` | `#FCEDE4` | `#33211A` |
    | `--eci-diff-del-fg` | `#A8471B` | `#F0A27A` |

  - **New classes** (tokens and `color-mix` only):
    - `.eci-ledger`, `.eci-slot` and `.eci-slot-empty`;
    - `.eci-answer-row` and `.eci-answer-head`;
    - `.eci-diff-split`, `.eci-diff-unified`, `.eci-diff-line`, `.eci-diff-gutter` and `.eci-diff-quoted`;
    - `.eci-case-facts`, `.eci-case-timeline` and `.eci-case-card`;
    - `.eci-role-chip` and `.eci-status-banner`.
  - **Diff view switching.** `@media (max-width: 639px)` hides `.eci-diff-split` and shows `.eci-diff-unified`.

## 7. Accessibility and mobile

- **Headings.** One `h1` per page. Year groups and sections are `h2`, and rows and items are `h3`.
- **Colour is never the only carrier:**
  - status chips carry text;
  - diff changes use `<del>`/`<ins>`, strike and underline, and hidden `Removed:`/`Added:`;
  - chart marks differ by fill vs dashed ring, plus a legend;
  - joint objections have a connector plus a legend.
- **Keyboard.**
  - Every mark, card, row title and chip is a native link with a `2px solid var(--eci-ink)` focus-visible ring.
  - The drawer keeps Esc and focus return.
  - Anchor targets (`#objection-n`, `#charge-id`) get `scroll-margin-top: 72px`.
- **Screen readers:**
  - the objection chart is a `figure` with a caption, and its marks have aria-labels;
  - answer rows are `article`s with column labels in each cell;
  - diff columns are labelled by `before_label`/`after_label` through `aria-labelledby`;
  - the empty objection slots say `Objection not yet public`.
- **Mobile.** The pages must work at 400px with no horizontal scroll.
  - Objections: the ledger meta column moves above the body, and the chart keeps its full width through the `viewBox`, with month initials.
  - Answers: cells stack with their labels, and an empty record cell is omitted.
  - Rules: the diff uses the unified view, and long lines wrap (`overflow-wrap: anywhere`).
  - Courts: cards and facts go to one column, and the timeline rail stays at the left.
- **Reduced motion.** There are no new animations. Hover transforms are wrapped in `@media (hover: hover)` and disabled under `prefers-reduced-motion`.

## 8. Work split and hotspots

The two workers run in parallel against this spec. The contract between them is §4 (shapes) and the
expected values in §4.2, §4.3 and §9. Both rebase on phase 4 before merging. In shared files, they append
inside a `// ECI Files phase 5` (or `# ECI Files phase 5`) block and never reorder earlier code.

**BACKEND worker owns:**

- `backend/database/migrations/versions/0009_eci_files_views.py` (new);
- `ingestion/neta_ingest/pipelines/curated/eci_files.py`, `ingestion/tests/test_eci_files.py`, and `ingestion/tests/fixtures/eci_files/extra/*` (new fixture files);
- **`api/neta_api/schemas.py`** (sole editor), plus `services/eci_files.py` and `routers/eci_files.py`;
- `api/tests/test_eci_answers.py` (new);
- `docs/eci-files/openapi.json` (regenerate) and `docs/OPERATIONS.md` (the ECI Files section: the new files and tables);
- the data files, for fixes only. The backend worker may correct a data file if validation finds a real error, but must say so in the PR. It must not change curation (which rows, which records, which lines).

**WEB worker owns:**

- `web/src/app/eci-files/objections/page.tsx`, `answers/page.tsx`, `rules/page.tsx`, `rules/[diff]/page.tsx`, `courts/page.tsx` and `courts/[case]/page.tsx` (all new);
- `web/src/app/eci-files/timeline/page.tsx` (switch to `DrawerFromParam` only);
- **New files in `web/src/components/eci-files/`:**
  - `DrawerFromParam`, `EntryRefLink`, `ObjectionStrip`, `ObjectionLedger`;
  - `AnswerRow`, `TextStatusBadge`, `RuleDiffView`;
  - `CaseCard`, `CaseFacts`, `CaseTimeline`, `RoleChip`;
- **Edits:** `EntryDetail.tsx` (the context block), `QuestionCards.tsx` (four cards) and `skeletons.tsx` (one skeleton per new page);
- `web/src/lib/eci-diff.ts` (new) and `web/src/lib/eci-files.ts` (`linkifyFollowedBy`, and the role, status and text-status label maps);
- **`web/src/lib/api.ts`**, **`web/src/types/eci-files.ts`** and **`web/src/app/globals.css`** (sole editor of all three), plus `web/src/types/api.ts` (codegen only).

**Hotspots, and who else touches them:**

| file | who else touches it | rule |
| --- | --- | --- |
| `schemas.py` | phases 3 and 4 | backend worker only; `EciEntryRef` gains one optional field and nothing else changes |
| `services/eci_files.py` | phases 3 and 4 | add functions; don't change existing signatures |
| the loader | phases 3 and 4 | add paths, models and a replace block; don't touch lane or state logic |
| `api.ts`, `types/eci-files.ts`, `lib/eci-files.ts`, `globals.css` | phases 3 and 4 | web worker only; append |
| `EntryDetail.tsx` | phases 3 (`TIER_LABEL`) and 4 (`basePath`) | add the context block at the end, before sources |
| `QuestionCards.tsx` | phase 3 | append cards |

Neither worker touches `sitemap.ts`, `SiteHeader`, the homepage or `robots.ts`. Each worker makes one
commit covering its code and docs.

## 9. Acceptance checks

**Storage and loader**

- [ ] `alembic upgrade head` reaches `eci_files_views_0008`. `downgrade -1` then `upgrade head` round-trips, and `alembic check` is clean.
- [ ] `neta eci-files` prints `loaded 11 objections (3 missing), 61 pairs (27 without a response), 7 rule diffs, 5 cases (51 items)` and `resolved 5 response links through merges.json`.
- [ ] Running it twice leaves identical row counts in all eleven tables.
- [ ] `pytest` passes: the ingestion tests (with and without `NETA_TEST_DATABASE_URL`) and `api/tests`. `ruff check` passes for ingestion, backend and api.

**API**

- [ ] `/eci-files/objections`: 11 objections, `missing` 3, `reported_total` 14; Sandhu 8 (joint 2), Joshi 5 (joint 2); `response.id` is `sir-rules-eci-pn-119-response`; objection 5's `followed_by_refs` holds `sir-rules-form6-online-sir-declaration`.
- [ ] `/eci-files/answers`: 61 rows, 0 of them `curated: false`, `without_response` 27, `with_record` 14. `?view=no-response` returns 27 rows with the same counts.
- [ ] `/eci-files/rules`: `counts` is `{rules: 39, with_diff: 6, diffs: 7}`. `/eci-files/rules/diffs/nope` returns 404.
- [ ] `/eci-files/courts`: 5 cases in file order. `/eci-files/courts/bihar-sir` has 10 items whose last non-related item is `sir-rules-sc-sir-judgment`. `/eci-files/courts/narnia` returns 404.
- [ ] `/eci-files/entries/sir-rules-form6-online-sir-declaration` has `context.pairs[0].role == "charge"` and `context.rule_diffs[0].id == "form-6-online-last-sir"`.
- [ ] `/eci-files/entries/officials-sandhu-form6-note` has `context.objections == [{n: 10, ...}]`.
- [ ] `/eci-files/entries/sir-rules-sc-sir-judgment` has `context.case.slug == "bihar-sir"`.

**Objections page**

- [ ] 14 `<li>` in the ledger: 11 numbered, and 3 dashed and labelled `Not yet public`.
- [ ] The response box sits above the ledger and opens `sir-rules-eci-pn-119-response` in the drawer.
- [ ] The chart shows 13 marks (8 in Sandhu's row, 5 in Joshi's), 2 joint connectors and 1 dashed ring (objection 9). Each mark jumps to its ledger item.
- [ ] Objection 5's `What followed` has a `(see entry)` link that opens the drawer and an `(objection 10)` link that jumps to the anchor.

**Answers page**

- [ ] 27 rows read `No response on record.`
- [ ] Exactly 14 rows have a third-column entry, and every one of those entries shows a `Document` chip.
- [ ] `#charge-sir-rules-form6-online-sir-declaration` shows two record entries, the Commission's response, and the note.

**Rules pages**

- [ ] `/eci-files/rules/rule-93-inspection` marks only `as specified in these rules` as inserted.
- [ ] `/eci-files/rules/form-6-online-last-sir` shows the paraphrase banner, per-column badges, quotation marks on the three option lines, and italic paraphrase lines.

**Courts pages**

- [ ] `/eci-files/courts/2023-act-challenge` lists 20 steps, the split-verdict reference last among the non-related items, and a facts panel with six petitioners.

**Every page**

- [ ] The drawer opens with `?entry=`, closes with Esc, and preserves the other params.
- [ ] 400px width has no horizontal scroll, and both themes are legible.
- [ ] Pages are `noindex`, not in the sitemap, and not in `SiteHeader`.
- [ ] `npm run lint`, `npm run typecheck` and `npm run build` pass with the API down, and the pages show the failure copy.
- [ ] No verdict words in UI copy. Grep the new files for `rigged|stolen|illegal|fraud|false claim|debunk`. They may appear only inside quoted entry text from the API.

## 10. Known data issues (for the data owner, not blockers)

- **Notes that cite excluded ids.** Eight claim entries' `notes` cite `statements-reporting-eci-press-note-differing-views`, which `merges.json` excluded; the kept id is `sir-rules-eci-pn-119-response`. The notes render as text, so nothing breaks, but the id in them is stale.
- **Duplicate charges that merges missed.** `pairs.json` records seven same-charge groups as `also_recorded_as` (open question 2):
  - the three records of the 23 Sep investigation;
  - Rahul Gandhi's dissent note (3 entries);
  - Mahadevapura / vote chori;
  - Aland;
  - the Maharashtra op-ed;
  - Goa's 97 voters (3 entries);
  - the Form 6 change (3 entries).
- **`courts-case-bihar-sir` summary.** It says the Court traced the power to "Section 21(3) of the Registration of Electors Rules, 1960". `sir-rules-sc-sir-judgment` says Section 21(3) of the RP Act, 1950. One of them is wrong. The case page shows the case summary, so fix the case entry before launch.

## Open questions for the owner

1. **Rows where the Commission acted first.** Some rows are not charges against the Commission: the Mamata Banerjee campaign ban, the West Bengal suspension order, the 17C notice, and others (§1.2).
   - (a) Keep them on `/answers` under the neutral heading `What was said or done`.
   - (b) Drop them from `/answers` and show the pairing only in the drawer.
   - (c) Give them their own section, `Commission actions and responses`.

   **Recommendation: (a).** Every response in the record then sits beside what it answers, and nothing is hidden.
2. **Seven duplicate charge groups that `merges.json` did not merge.**
   - (a) Leave them as `also_recorded_as` in `pairs.json` (as built).
   - (b) Add them to `merges.json` now and rerun `scripts/eci_files_reconcile.py`.
   - (c) Both: ship (a), and schedule (b) for the next data pass.

   **Recommendation: (c).** Merging changes entry ids other phases may cite, so it should not ride on this phase.
3. **The Form 6 diff has no primary text on either side.**
   - (a) Publish it with the paraphrase banner and per-line quote marks (as built).
   - (b) Hide it until the Gazette Form 6 (the 17 Jun 2022 amendment) and a portal capture are sourced.
   - (c) Show only the quoted after-options as a "What the online form asks" box, with no diff styling.

   **Recommendation: (a).** It is labelled on every line, and it is the rule change the investigation turns on. Pull the Gazette Form 6 in the next research pass to move the before side to verbatim.
4. **A third text status, `quoted in reporting`.**
   - (a) Keep three statuses (as built).
   - (b) Fold it into `paraphrased from reporting`.

   **Recommendation: (a).** An exact quotation reported by a newspaper is stronger than a paraphrase, and the reader should see which lines are which.
5. **The 2023 Act text came from the bill plus the list of amendments, because India Code was blocked this session.**
   - (a) Keep `verbatim` and make fetching `a2023-49.pdf` a pre-launch check (as built; see the diff `note`).
   - (b) Mark both sides of those two diffs `quoted in reporting` until checked.

   **Recommendation: (a).** Clause 7 and clause 17 were not amended in passage, so the wording matches. The check only confirms it.
6. **The empty-slot label.**
   - (a) `Not yet public` (the brief's words).
   - (b) `Not itemised in the published reports`.

   **Recommendation: (b), or keep (a) with the explanatory line (as built).** "Not yet public" implies they will be published. The record only supports "not itemised", since the notes may already be public elsewhere. This is a copy decision, so it is yours.
7. **Strictness of "What the record shows".**
   - (a) Documented entries only (as built: 14 rows).
   - (b) Also allow tier-1 or tier-2 reported entries.

   **Recommendation: (a).** A reported entry beside a claim invites reading it as a finding. The column exists to show primary documents, and it is blank otherwise.
