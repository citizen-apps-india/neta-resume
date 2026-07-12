# Future features — "more data for citizens" (contributions welcome)

This is a researched wishlist of ways to give citizens **more** than neta-resume shows today. It came out of a
"what more can we give citizens" review of the Indian civic-data landscape. Each idea is tagged with its
**citizen value**, the **real data source** (+ license + granularity), an honest **feasibility / blocker**
note, rough **effort**, and where it would **hook into the codebase** — so a contributor can pick one up.

> **If you want to contribute one of these**, open an issue first to claim it. Anything tagged **Feasible now**
> is a good starting point — the data already exists and the patterns to reuse are named below.

## Non-negotiables (any feature must honour these)

- **No fact without a source.** Every stored fact carries a `source_ref` + trust tier (1 official · 2
  ADR/TCPD/PRS · 3 reported). See `docs/schema.md`, `packages/neta-core/neta_core/provenance.py`.
- **Descriptive, never a value judgment.** We show *what* the record says, sourced — not "good/bad" rankings.
- **Non-commercial**, and prefer openly-licensed sources (GODL-India / CC / public record). MyNeta/ADR is
  non-commercial, no bulk CSV — respect it.
- **Missing ≠ zero.** Absent data renders `—`, never `0`.
- **Reuse the patterns.** Ingestion = idempotent upsert + provenance (`ingestion/neta_ingest/pipelines/…`);
  read = `api/neta_api/services` + `routers`; web = server components + the design system in
  `web/src/app/globals.css` (`.nr-bento`/`.nr-cardgrid`/`AggregateLens`/`charts.tsx`).

---

## ✅ Shipped

- **Profile depth** — education level + age (+ gender where declared) on directory cards; father/spouse name
  and home state on profiles. All from data we already store. (PR #79.)

---

## 🟢 Feasible now — good contributions

### 1. "Who Represents Us" analytics
**What:** the human-facts counterpart to the existing *Parliament functioning* section — House **composition**
(women %, median age, education mix, crorepati %), **wealth distribution** (median + percentiles), **year-over-
year wealth growth**, and **criminalisation** (share with pending cases, severity mix) — sliced by party /
state / cycle, plus a per-MP percentile ("assets in the 73rd percentile of the 18th LS").
**Citizen value:** High — turns latent affidavit data into system-level accountability trends.
**Data:** 100% our OWN tables (`person`, `affidavit`, `criminal_case`, `office_term`). No new sourcing.
**Feasibility:** **Feasible now.** Read-time aggregate.
**Effort:** M.
**Reuse:** `api/neta_api/services/parliament.py::theme_focus_by` (group-by-party/state pattern),
`percentile_cont` (see the `ActivityMetric` percentile in `services/resume.py`), web `AggregateLens`,
`components/resume/charts.tsx` (Donut / stacked / bars), `StatCard`/`SectionCard`, `.nr-cardgrid`.
**Notes:** gender coverage is partial (backfilled from Wikidata for the 18th LS) — report "of N with gender on
record". RS members file no candidate affidavit, so wealth/education/age are LS-rich, RS-sparse (honest `—`).

### 2. Parliamentary committees
**What:** which committees an MP sits on (Finance, Public Accounts, …) and their role — real legislative power
beyond attendance.
**Citizen value:** High.
**Data:** **sansad.in** committee pages (official, trust tier 1). Already the roster/contacts source.
**Feasibility:** **Feasible now.** Clean scrape + name-match to existing persons.
**Effort:** M.
**Reuse:** mirror `ingestion/neta_ingest/pipelines/enrich/attendance.py` (enumerate → `best_match`/
`normalize_name` → upsert with `record_source_ref`). New tables `committee` + `committee_membership`
(next migration is `0028`). Surface in the profile "Career & Roles" area.

---

## 🟡 Blocked on data access (need a source breakthrough)

### 3. MPLADS fund tracking ("follow the money")
**What:** local-area development funds **allocated / released / sanctioned / spent / unspent** per MP /
constituency, with utilisation %.
**Citizen value:** High.
**Data reality (the blocker):**
- Open & clean **data.gov.in (GODL)** has MPLADS, but the MP-wise granular dataset is only **16th Lok Sabha
  (2014–19)** — mostly *former* MPs. See the [MPLAD keyword index](https://www.data.gov.in/keywords/MPLADS)
  and ["Utilisation of MPLAD funds — 16th LS MPs"](https://www.data.gov.in/catalog/utilisation-mplad-scheme-funds-and-detail-works-16th-lok-sabha-mps).
- **Current 18th-LS** per-MP funds live on the official portal
  [mplads.gov.in](https://www.mplads.gov.in/) / e-SAKSHI — **form-gated**, slow, and detail likely needs login.
- Structured current data exists on [dataful.in](https://dataful.in/collections/589/) (Factly) but it's a
  **commercial** platform → conflicts with the non-commercial ethic.
**Feasibility:** **Blocked** for the *current* term. Options a contributor could unblock: (a) confirm a current
GODL dataset on data.gov.in; (b) a polite scraper for the public portal if per-MP figures are viewable without
login; (c) ship the 16th-LS open data as an explicitly-labelled *historical* layer.
**Units:** ₹ **lakh** (not rupees) — convert on ingest. **Gap:** MPLADS was suspended Apr 2020–Mar 2022 (COVID)
— mark as suspended, don't impute.
**Reuse:** the registered `datagovin` source (`db/seeds/sources.sql`) — but its client
(`packages/neta-sources/neta_sources/datagovin/client.py`) is currently a stub needing an OGD API key.

### 4. Election / campaign expenditure + electoral bonds
**What:** candidate campaign spend (ECI statements); political-party donations.
**Data:** ECI candidate expenditure PDFs (need OCR); ADR analyses; electoral-bond data is partly restricted
post-2024.
**Feasibility:** Blocked/hard (OCR + restricted bond data). Effort L.

### 5. Open data API / bulk export (for researchers & journalists)
**What:** a documented read API + bulk JSON/CSV of the deduplicated, sourced record.
**Citizen value:** High (multiplies external scrutiny).
**Feasibility:** **Blocked on policy, not tech** — the MyNeta/ADR non-commercial license and a **DPDP Act**
review (republishing criminal data) must be resolved first. Needs a licensing decision, then it's mostly
engineering.

---

## 🔭 Bigger / later

- **Bills & legislation** — bill status + **sponsorship** + which member introduced/debated (PRS / sansad).
  ⚠️ India publishes **no individual MP votes** on bills (divisions record only the aggregate outcome) — track
  sponsorship + debate participation, never fabricate a "voted yes/no". Effort M.
- **Budget & scheme context** — Union/ministry allocations + scheme dashboards (data.gov.in / Open Budgets
  India, GODL/CC) as a *context* layer alongside a constituency. Not legislator-specific. Effort M.
- **Granular affidavit line-items** — the `affidavit_line_item` table (migration 0006) exists but is unused;
  the MyNeta parser (`packages/neta-sources/neta_sources/myneta/parser.py`) only extracts section totals.
  Extend it to capture per-line assets (cash / jewellery / land) + profession. Effort M.

---

## ❌ Out of scope (documented so nobody re-investigates)

- **Individual MP voting records** — India does not publish per-member votes; this is a structural gap, not a
  sourcing problem. (Sponsorship + debate participation is the closest available signal.)
- **Manifesto / promise tracking** — assessing "promise kept?" is inherently editorial and labour-heavy;
  violates "descriptive, never a judgment". Better to link out to third-party trackers as reported sources.
- **Ward / municipal councillors** — 31+ state election bodies, no unified source, extreme fragmentation.
  Revisit only after state-assembly coverage is stable (there is a municipal stub today).

---

*Have data we don't? A cleaner open source for one of the blocked items? Open an issue — that's the highest-
leverage contribution.*
