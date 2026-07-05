# Data dictionary

Per-table, per-column reference for the core tables. **Source of truth is `db/migrations/*.sql`**
(this doc tracks them; `db/schema.dbml` is the ERD). Enums below are the literal `CHECK`-constraint values.

> **Provenance:** every *fact* table carries a `source_ref_id` (FK → `source_ref`) — the pointer back to
> the source record + cached snapshot. "No fact without a source."

## Valid values / enums

| Column | Values | Meaning |
|---|---|---|
| `house.jurisdiction` | `union`, `state` | LS/RS are `union`; assemblies/councils `state`. |
| `office_term.membership_type` | `elected`, `nominated`, `byelection` | default `elected`. |
| `office_term.status` | `sitting`, `former`, `disqualified`, `resigned` | default `sitting`. |
| `party_affiliation.detection` | `structured_term_diff`, `manual`, `news_derived` | how the affiliation was derived. |
| `criminal_case.status` | `pending`, `convicted`, `acquitted`, `framed_charges` | default `pending`. |
| `criminal_case.severity` / `legal_section.base_severity` | `heinous`, `serious`, `minor` | **derived** (case = max over charges). Nullable. |
| `legal_section.code_system` | `IPC`, `BNS`, `PCA`, `RPA` | Penal Code / new code / Prevention of Corruption / Representation of the People. |
| `source.trust_tier` | `1`, `2`, `3` | 1 official, 2 ADR/TCPD/PRS, 3 reported/news. |

**`office_term.attendance_pct`** — `numeric(5,2)`, cumulative parliamentary attendance % from PRS for the
current term. **`NULL` is meaningful:** rule-exempt members (ministers, PM, Speaker/Dep. Speaker, LoP)
don't sign the register, so they have no % → renders `—`, **never 0**. Provenance:
`office_term.attendance_source_ref_id`.

---

## Reference / spine tables (no provenance pointer; reference data)

### `house`
| Column | Type | Notes |
|---|---|---|
| `id` | smallserial PK | |
| `code` | text UNIQUE | `'LS'`,`'RS'`,`'MH_VS'`,… |
| `name` | text | display name |
| `jurisdiction` | text CHECK | `union` \| `state` |
| `state_code` | text | NULL for LS/RS |

### `term_cycle`
| Column | Type | Notes |
|---|---|---|
| `id` | bigserial PK | |
| `house_id` | smallint FK→house | |
| `number` | int | 17, 18, …; UNIQUE `(house_id, number)` |
| `start_date` / `end_date` | date | RS modelled as one current cohort |
| `eci_election_id` | text | ties to ECI/MyNeta partition (`LS2024`, `RS-CURRENT`) |

### `party`
| Column | Type | Notes |
|---|---|---|
| `id` | bigserial PK | |
| `canonical_name` | text | |
| `abbr` | text | `BJP`,… |
| `eci_party_id` | text | |
| `is_active` | boolean | default true |

`party_alias(party_id, alias, source)` — spelling variants → canonical party; UNIQUE `(party_id, alias)`.

### `source`
| Column | Type | Notes |
|---|---|---|
| `id` | smallserial PK | |
| `code` | text UNIQUE | `'sansad'`,`'myneta'`,`'tcpd_surf'`,`'bharat_courts'`,`'prs'`,`'eci'`,`'datagovin'`,`'wikidata'`,`'news'` |
| `name` | text | |
| `base_url` | text | |
| `license` | text | e.g. `non-commercial` for MyNeta/ADR |
| `trust_tier` | smallint | default 2 — see enum table |

---

## Identity

### `source_ref` — native record identity in a source (the provenance anchor + idempotency key)
| Column | Type | Notes |
|---|---|---|
| `id` | bigserial PK | |
| `source_id` | smallint FK→source | |
| `native_id` | text | sansad `mpsno` (namespaced `ls-`/`rs-`), myneta candidate_id, … |
| `native_url` | text | live link to the source page |
| `person_id` | bigint FK→person | **NULL until entity-resolved** |
| `raw_name` | text | name as seen in the source |
| `raw_payload_ref` | text | path/hash into `ingestion/data/raw_cache/` snapshot |
| `fetched_at` | timestamptz | default now() |

**UNIQUE `(source_id, native_id)`** — the dedup/idempotency key for all upserts.

`fact_source(source_ref_id, observed_at, retrieved_at, note)` — generic multi-source provenance edge, used
when one fact is corroborated by several sources.

### `person` — canonical person (stable across houses/elections)
| Column | Type | Notes |
|---|---|---|
| `id` | bigserial PK | internal surrogate; **never** a source's native id |
| `display_name` | text | |
| `normalized_name` | text | transliteration-normalized key (search + ER blocking; `pg_trgm` GIN) |
| `gender` | text | |
| `birth_year` | int | |
| `tcpd_surf_id` | text UNIQUE | seeded from TCPD where available |
| `wikidata_qid` | text | |
| `photo_url` | text | official photo — sansad.in for MPs, MyNeta candidate image for state MLAs; proxied + disk-cached by the API. Added in 0008 |
| `home_state` | text | derived match feature: modal `office_term` state / `rs_state_code`. Refreshed by `neta derive-signals`. Added in 0021 |
| `relative_name` | text | derived match feature: the S/o\|D/o\|W/o relative from the person's latest affidavit — a decisive cross-house disambiguation signal. Added in 0021 |
| `phonetic_key` | text | derived match feature: metaphone-over-sorted-tokens key so the stitcher blocks same-sound / different-spelling names (Muhammad≡Mohammed). Refreshed by `neta derive-signals`. Added in 0023 |
| `created_at` / `updated_at` | timestamptz | |

`person_name_variant(person_id, variant, source_id, script)` — every observed spelling; `script` is
`'latin'` or `'devanagari'`; UNIQUE `(person_id, variant, source_id)`.

---

## Fact tables (each carries provenance)

### `office_term` — one posting in a legislature (the roster spine) — *provenance: `source_ref_id` (+ `attendance_source_ref_id`)*
| Column | Type | Notes |
|---|---|---|
| `id` | bigserial PK | |
| `person_id` | bigint FK→person | |
| `house_id` | smallint FK→house | |
| `term_cycle_id` | bigint FK→term_cycle | |
| `constituency` | text | LS/assembly seat; NULL for RS |
| `rs_state_code` | text | state an RS member represents |
| `ls_state_code` | text | the seat's state — the LS constituency's state, or a state-assembly member's state (e.g. `Maharashtra` for MH_VS). Surfaced as `PersonSummary.state`. |
| `membership_type` | text CHECK | `elected`\|`nominated`\|`byelection` (default `elected`) |
| `start_date` / `end_date` | date | |
| `party_id` | bigint FK→party | party **at time of this term** (drives switch detection) |
| `status` | text CHECK | `sitting`\|`former`\|`disqualified`\|`resigned` (default `sitting`) |
| `source_ref_id` | bigint FK→source_ref **NOT NULL** | provenance |
| `attendance_pct` | numeric(5,2) | PRS cumulative %; NULL = exempt/unknown (renders `—`) |
| `attendance_source_ref_id` | bigint FK→source_ref | provenance for the attendance figure |

UNIQUE `(person_id, term_cycle_id, constituency)`.

`cabinet_post(person_id, title, body, start_date, end_date, source_ref_id)` — ministerial/leadership
offices; provenance: `source_ref_id`.

### `party_affiliation` — membership of a party over a date range — *provenance: `source_ref_id`*
| Column | Type | Notes |
|---|---|---|
| `id` | bigserial PK | |
| `person_id` | bigint FK→person | |
| `party_id` | bigint FK→party | |
| `joined_date` / `left_date` | date | |
| `is_current` | boolean | default false; partial UNIQUE index on `(person_id) WHERE is_current` |
| `join_reason` / `leave_reason` | text | **REPORTED** narrative (UI labels it so) |
| `detection` | text CHECK | `structured_term_diff`\|`manual`\|`news_derived` |
| `confidence` | smallint | 0..100, default 50 |
| `source_ref_id` | bigint FK→source_ref **NOT NULL** | source for the affiliation fact |

### `party_switch_event` — explicit from→to switch — *provenance: `narrative_source_ref_id` (narrative)*
| Column | Type | Notes |
|---|---|---|
| `id` | bigserial PK | |
| `person_id` | bigint FK→person | |
| `from_party_id` | bigint FK→party | nullable |
| `to_party_id` | bigint FK→party **NOT NULL** | |
| `event_date` | date | |
| `narrative` | text | **REPORTED** "why", clearly labelled |
| `narrative_source_ref_id` | bigint FK→source_ref | source for the narrative (typically tier 3) |
| `detected_from` | text | default `term_diff` |

### `affidavit` — ECI affidavit per election cycle (assets/liabilities/income) — *provenance: `source_ref_id`*
| Column | Type | Notes |
|---|---|---|
| `id` | bigserial PK | |
| `person_id` | bigint FK→person | |
| `source_ref_id` | bigint FK→source_ref **NOT NULL** | MyNeta candidate-page partition |
| `election_cycle` | text | `'LS2024'`,… (drives YoY) |
| `house_id` | smallint FK→house | |
| `filed_year` | int | YoY ordering key |
| `age` / `education` | int / text | |
| `total_assets` / `total_liabilities` | bigint | **integer rupees**, default 0 |
| `movable_assets` / `immovable_assets` | bigint | nullable |
| `self_income` | bigint | declared income (ITR where present) |
| `income_year` | int | |
| `pan_given` | boolean | |
| `raw_url` | text | direct affidavit page link (shown in UI) |
| `relative_name` | text | the S/o\|D/o\|W/o relative printed on the affidavit; `''` = fetched but none. Added in 0020 |
| `relation_type` | text | `father`\|`spouse`\|`guardian` when a specific marker is present, else null (MyNeta's label is usually the generic "S/o\|D/o\|W/o"). Added in 0020 |

UNIQUE `(person_id, election_cycle, source_ref_id)`.

`affidavit_line_item(affidavit_id, category, label, amount, owner)` — granular breakdown;
`category` ∈ `asset_movable`/`asset_immovable`/`liability`/`income`; `owner` ∈ `self`/`spouse`/`dependent`;
`amount` integer rupees; cascades on affidavit delete.

### `legal_section` — IPC/BNS section catalog + crosswalk (reference seed)
| Column | Type | Notes |
|---|---|---|
| `id` | bigserial PK | |
| `code_system` | text CHECK | `IPC`\|`BNS`\|`PCA`\|`RPA` |
| `section_number` | text | `'302'` |
| `title` | text | |
| `ipc_equivalent` / `bns_equivalent` | text | IPC↔BNS crosswalk |
| `base_severity` | text CHECK | `heinous`\|`serious`\|`minor` (nullable) |
| `is_cognizable` | boolean | |
| `max_punishment_years` | int | `99` encodes life/death |

UNIQUE `(code_system, section_number)`. Seeded from `db/seeds/ipc_bns_sections.sql`; `severity_rules.sql`
can re-derive `base_severity` numerically. The seed mirrors each curated IPC section as its **BNS
counterpart** (BNS replaced the IPC on 2024-07-01) with the same severity, so post-2024 affidavits
(e.g. state-assembly cases) are assessed identically. The API surfaces each charge as `{raw, title,
equivalent}` (the `equivalent` from the `ipc_equivalent`/`bns_equivalent` crosswalk) so the profile can
show e.g. "BNS 103 ≈ IPC 302 · Murder". Sections outside the curated catalog stay unclassified (by design,
IPC and BNS alike).

### `criminal_case` — a declared/tracked case — *provenance: `source_ref_id` (+ `court_source_ref_id`)*
| Column | Type | Notes |
|---|---|---|
| `id` | bigserial PK | |
| `person_id` | bigint FK→person | |
| `affidavit_id` | bigint FK→affidavit | the filing it was declared at (nullable) |
| `source_ref_id` | bigint FK→source_ref **NOT NULL** | provenance |
| `case_number` / `court` / `filed_year` | text/text/int | |
| `status` | text CHECK | `pending`\|`convicted`\|`acquitted`\|`framed_charges` (default `pending`) |
| `is_convicted` | boolean | default false — **mostly pending; never assert guilt** |
| `severity` | text CHECK | `heinous`\|`serious`\|`minor` — **DERIVED** (max over charges) |
| `severity_rule_version` | text | which rubric produced it (auditability) |
| `description` | text | |
| `cnr_number` | text | eCourts CNR for court enrichment linkage |
| `court_source_ref_id` | bigint FK→source_ref | live status from bharat-courts/eCourts |

`case_charge(criminal_case_id, section_id, raw_section_text)` — IPC/BNS sections on a case (many per case);
`section_id` FK→legal_section (nullable until resolved); `raw_section_text` as scraped; cascades on case delete.

### `person_merge_candidate` — cross-house identity-stitcher review queue + audit (added in 0022)
| Column | Type | Notes |
|---|---|---|
| `person_lo` / `person_hi` | bigint FK→person (ON DELETE SET NULL) | the proposed-merge pair, ordered min/max; a side nulls out when merged away (audit survives via `evidence.pair`) |
| `score` | numeric | 0..1 from `stitch_score.score_person_pair` |
| `band` | text | `auto_merge` \| `review` \| `reject` |
| `evidence` | jsonb | per-signal breakdown (name/relative/birth/state/party/gender) + `pair` + vetoes |
| `rule_version` | text | scorer version (`stitch-v1`); a `rejected` pair is re-proposed only if this changes |
| `status` | text | `pending` (awaiting review) \| `accepted` \| `rejected` (suppressed) \| `auto_merged` |
| `decided_by` / `decided_at` | text / timestamptz | `auto` for auto-merges, else the reviewer |

Populated by `neta stitch-identities`; reviewed via `neta review list|show|accept|reject`.
