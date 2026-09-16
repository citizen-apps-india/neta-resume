# Full historical Lok Sabha rosters — phased plan

> **Status:** deferred / not started. Design doc for restoring full past-session rosters in the Lok
> Sabha session selector. No code or ingest has been done yet.

## Context / problem

The Lok Sabha page's session selector shows past sessions as **incumbent-scoped**: 18th = 544 but
17th ≈ 177, 16th ≈ 98, 15th ≈ 54, instead of the full ~543 each. Only MPs who are **also** in the
sitting 18th LS appear for past sessions.

**Root cause (confirmed in code):** `_prune_non_current()` in
`ingestion/neta_ingest/pipelines/identity/merge_cycles.py` deletes the entire person (cascading all
their terms) for anyone who does **not** hold a term in the latest cycle of their house (or any RS
cycle). Past-cycle winners were ingested "solely to backfill current members' history" and then
pruned. The 54/98/177 are the survivors — incumbents who also won those prior cycles.

**The API/web plumbing already works** for full rosters: `_summary_base(cycle)` + `cycles_group()`
in `api/neta_api/services/resume.py` project each row "as it stood" in the chosen cycle and count
members per cycle. If the per-cycle `office_term` rows existed, `/persons?cycle=17` and the session
facet would surface all ~543 automatically. **Only the data is partial.**

**Key hazard to manage:** simply keeping historical persons would pollute the *current* views.
`_set_cycle_status()` marks each person's own most-recent term `sitting`, so a kept 17th-only MP would
be flagged sitting and leak into the default `/lok-sabha` (18th), `/directory`, the homepage preview,
and the `/stats` "Lok Sabha" count. So "sitting/current" must become **absolute** (latest cycle of the
house / RS-current), not per-person-relative.

## Design decision — keep current views clean

Historical former MPs appear **only** in the cycle-scoped session-selector views (15th/16th/17th). The
sitting 18th roster, `/directory` house views, the homepage widget, and the `/stats` LS/RS counts stay
scoped to currently-sitting members (~544 LS). `total_legislators` (homepage "Legislators on file
(growing)") may grow — that's on-brand.

## Open decision (decide at execution time)

Backfill scope / order — recommended **phased: 17th first, then 16th + 15th** (verify current-view
cleanliness in prod after the first cycle). Alternatives: all three at once; or 17th only. The code
changes below are identical regardless — scope only changes which ingest jobs are triggered.

---

## Phase 1 — Code: absolute "sitting" + stop pruning (ingestion)

File: `ingestion/neta_ingest/pipelines/identity/merge_cycles.py`

1. **`_set_cycle_status()`** — redefine `sitting` absolutely so it matches the prune keep-condition:
   `sitting` iff `house.code = 'RS'` **or** `term_cycle.number = max(number for that house_id)`; else
   `former`. (Replaces the per-person `max(start_date)` rule. Handles the cross-house "MLA→MP" case:
   the old state term is non-latest → former; the LS18 term → sitting. Dual-current is rare/acceptable.)

2. **Disable the prune** in the default flow: change `run(prune: bool = True)` → default `False` (keep
   the param + `_prune_non_current` for optional use, but the `merge-cycles` CLI no longer deletes
   prior-cycle-only winners). Confirm the CLI wrapper in `ingestion/neta_ingest/cli.py` passes through.

3. No schema change. `party_affiliation.is_current` is already `false` for past-cycle ingests
   (myneta sets `is_current = is_latest_cycle`), so historical persons correctly have no current party.

## Phase 2 — Code: scope current-only projections to sitting (API)

File: `api/neta_api/services/resume.py`

1. **Default `_summary_base(None)`** — the `oh` LATERAL must only surface a **sitting** term so
   past-only MPs get `current_house = NULL` (and thus drop out of `house='Lok Sabha'` / current
   filters): set `term_filter = "WHERE ot.person_id = p.id AND ot.status = 'sitting'"` and simplify
   `term_order` to date-desc. (Cycle-scoped branch unchanged — session browsing already works.)

2. **`_STATS_SQL`** — scope the `lok_sabha` and `rajya_sabha` counts to sitting terms
   (`AND ot.status = 'sitting'`) so the headline stays ~544 LS after historical persons are added.
   Leave `total_legislators = count(*) person` (grows intentionally).

3. No response-shape change (pure projection change), so no `npm run codegen` needed.

**Verification (Phases 1–2, local):** `uv run pytest`; `uv run ruff check packages ingestion`;
`cd api && uv run ruff check .`. On a local DB with ≥2 LS cycles ingested: after `neta merge-cycles`,
assert (a) `/persons?house=Lok Sabha` (no cycle) returns only sitting-18 members, (b)
`/persons?cycle=17` returns the full set present, (c) `/stats` `lok_sabha` unchanged, (d) a known
past-only winner has `current_house` NULL in the default list but appears under `cycle=17`.

## Phase 3 — Data: backfill past-cycle winners (ops, via GitHub Actions `ingest.yml`)

The pruned persons are gone and CI runners have no persistent `raw_cache`, so this **re-scrapes**
MyNeta. Per cycle (~540 winners), run in order via `workflow_dispatch` (concurrency group `ingest`):

```
neta myneta --cycle LS2019 --limit 1000     # (then LS2014, LS2009) — creates a person + former
                                            #   office_term + affidavit + criminal cases per winner
neta merge-cycles                            # no-prune now: stitches incumbents, KEEPS past-only winners
neta canon-parties                           # merge abbr/full party dupes
```

- Idempotent: myneta upserts on `source_ref.native_id = "{cycle}:{candidate_id}"` (cycle-namespaced —
  MyNeta candidate_ids repeat across cycles); incumbents' existing past source_refs update in place,
  past-only winners are (re)created.
- Politeness / rate-limit via `neta_core.http`; batch through CI, never the laptop.
- **Phased:** run LS2019 first → deploy/verify → then LS2014 + LS2009.

**Cost:** ~540 candidate-page fetches per cycle (~1,600 for all three), rate-limited (tens of minutes
of CI per cycle). Adds ~1,000+ former-MP profiles to the DB (visible only in session views).

## Phase 4 — Verify end-to-end (prod)

- Session facet on `/lok-sabha`: 17th (then 16th/15th) shows ~543, 18th still 544.
- Switch to 17th → full roster renders with at-the-time party/constituency/assets; spot-check a
  past-only former MP (e.g. someone who lost their seat in 2024) now appears for 17th but **not** in the
  default 18th roster, `/directory` current view, homepage widget, or the `/stats` LS count.
- Confirm no regression to the sitting-18 roster count, RS roster, or state-assembly current views.

## Critical files

| Area | Files |
|---|---|
| Prune + sitting status | `ingestion/neta_ingest/pipelines/identity/merge_cycles.py` (`_set_cycle_status`, `_prune_non_current`, `run`), `ingestion/neta_ingest/cli.py` (`merge-cycles`) |
| Current-only projection + stats | `api/neta_api/services/resume.py` (`_summary_base` default branch, `_STATS_SQL`) |
| Ingest entry points (data) | `neta myneta --cycle …` (`pipelines/identity/myneta.py`), `.github/workflows/ingest.yml` |
| Already-correct (no change) | session projection `_summary_base(cycle)` + `cycles_group()`; web session selector |

## Risks / notes

- Disabling the prune is global — past **state-assembly** backfill winners would also be kept. Harmless:
  default state views require `status='sitting'` → non-latest state winners stay `current_house` NULL
  (no state session selector exists yet).
- An MP who changed seats across cycles (won X in 2019, Y in 2024) won't merge (name+constituency rule)
  → appears once per cycle as separate persons. Pre-existing precision-over-recall behavior; acceptable.
- If a pre-prune DB dump / persistent `raw_cache` exists, Phase 3 could restore without re-scraping —
  otherwise re-scrape is required.
