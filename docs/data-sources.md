# Data Sources & Ingestion Pipeline Index

> Per-source index for Neta-Resume ingestion. Goal: **pipelines that fetch updatable data**, not a
> static dump. Confidence tags come from a 3-vote adversarial verification pass
> (✓ = confirmed; ⚠ = open question / unverified).

## TL;DR

```
   ROSTER  ──── sansad.in (LS/RS) + state assembly sites      → members + house IDs
   IDENTITY ─── TCPD SURF + Political Career Tracker (Ashoka)  → cross-election unique person ID
   AFFIDAVITS ─ MyNeta (ADR) + ECI affidavit portal            → assets, liabilities, income, criminal
   COURTS ───── eCourts / bharat-courts / openjustice S3       → live case status, severity enrichment
   CATALOG ──── data.gov.in OGD API (via datagovindia)         → bulk election/candidate datasets
```

**Reuse-don't-rebuild:** `nini1294/myneta_api` (scraper), `datameet/india-election-data` +
`Vonter/india-election-affidavits` (parsed affidavit corpus), `iamshouvikmitra/bharat-courts` +
`openjustice-in/ecourts` (court access), TCPD **SURF** (entity resolution), `addypy/datagovindia` (catalog).

---

## A. Roster — who is a legislator

### sansad.in (Digital Sansad — official LS & RS) — ✓ PRIMARY
- **URL:** https://sansad.in/ls/members · https://sansad.in/rs/members
- **Access:** structured member directory with member IDs (a "no API / no IDs" claim was *refuted* 0-3 → it **does** expose structured data/identifiers). Scrape-friendly HTML + likely JSON endpoints; stable per-member IDs.
- **Fields:** name, constituency, state, party, house term, profile (bio, debates, questions, attendance).
- **Pipeline:** scrape list → capture sansad member ID → fetch profiles. **Canonical roster + office-term spine.**
- **Cadence:** general election + by-elections + RS biennial retirements.

### State / UT legislatures — ⚠ HETEROGENEOUS
- ~31 separate sites, no unified API, many PDF-only member lists. Per-state adapters → common schema.
- Backfill history from **TCPD/LokDhaba** rather than scraping each archive.

### TCPD-IPD / LokDhaba (Ashoka) — ✓ historical backfill + ID backbone
- **URL:** https://lokdhaba.ashoka.edu.in · https://tcpd.ashoka.edu.in
- Every candidate/winner in every LS & State Assembly election since 1962, entity-resolved with stable IDs.

### PRS Legislative Research (mptrack) — ✓ attendance % (LS + RS)
- **URL:** https://prsindia.org/mptrack/18th-lok-sabha · https://prsindia.org/mptrack/rajya-sabha
- **Fields:** cumulative **attendance %** per member per term (the metric journalists cite), plus debates / questions / private-member bills. License non-commercial; every value source-cited.
- **Pipeline:** `neta attendance --house ls|rs` — paginate the listing (1-indexed `?page=N`) to enumerate members, match to our current-term person by normalized name, fetch each profile and write `office_term.attendance_pct` + a PRS `source_ref`. Idempotent; per-profile fetch is fault-tolerant.
- **Coverage is partial by design:** ministers, PM, Speaker/Dep. Speaker and the LoP don't sign the attendance register, so PRS shows no % → we leave it `NULL` (renders "—", never 0). State assemblies: not yet (no unified source).

---

## B. Affidavit data — wealth + criminal (the core)

### MyNeta (ADR / National Election Watch) — ✓ PRIMARY aggregator
- **URL:** https://www.myneta.info/
- ADR transcribes **ECI self-sworn affidavits** into structured per-candidate pages: total assets,
  liabilities, income (ITR), education, **criminal cases (counts + IPC sections + pending/convicted)**.
  Covers multiple LS elections **and** state assemblies.
- **⚠ Quality:** the "faithful, unmodified ECI mirror" claim was *refuted* (0-3) — ADR transcribes
  (OCR + manual), introducing its own processing. Cross-check raw ECI PDF for legal fidelity.
- **⚠ LICENSE:** ✓ non-commercial use only; ✓ **no CSV/bulk download**. Resolve before any commercial launch.
- **Reuse:** `nini1294/myneta_api` (✓ election-partitioned candidate data), `HarryStevens/adr-election-node`,
  `bkamapantula/parliamentary-candidates-affidavit-data`.

### ECI affidavit portal — ⚠ UNRELIABLE to fetch
- **URL:** https://affidavit.eci.gov.in/ (scanned PDF affidavits). Canonical legal source; flaky/scanned —
  verification only, **not** the primary ingestion path.

### Pre-parsed corpora (reuse) — ✓ backfill
- `Vonter/india-election-affidavits`, `datameet/india-election-data` (+ `affidavits/myneta.ipynb`).
  Seed/backfill so you're not re-OCRing years of PDFs; live-scrape only the latest cycle.

---

## C. Court records — live status & severity enrichment

> Affidavits are a point-in-time snapshot at nomination. For *current* status (charges framed, convicted,
> acquitted) enrich against the judiciary.

### eCourts Services (official) — ✓ PRIMARY, CAPTCHA-gated
- **URL:** https://services.ecourts.gov.in/ecourtindia_v6/ — case-status search exists but CAPTCHA-gated;
  single-case lookups. ("no API at all" was only 1-2 → semi-programmatic paths exist, no clean bulk API).

### bharat-courts — ✓ PRIMARY reuse
- https://github.com/iamshouvikmitra/bharat-courts — MIT, **async Python 3.1x**; a **public AWS S3 judgment
  archive** exists for backfill.

### openjustice-in/ecourts — ✓ PRIMARY reuse
- https://github.com/openjustice-in/ecourts — Python library/CLI; High Courts + benches coverage strongest.

**Severity:** neither ranks severity. Map IPC/BNS section → category using ADR's "serious criminal" rubric.
See `severity-rubric.md`.

---

## D. Catalog / bulk datasets

### data.gov.in (OGD) — ✓ PRIMARY
- **URL:** https://www.data.gov.in/apis — REST APIs (API-key). ✓ no native search API → use
  `addypy/datagovindia` (indexes the catalog). The "no political datasets" claim was *refuted* (0-3).

### OpenSanctions in_sansad — ✓ cross-validation
- https://www.opensanctions.org/datasets/in_sansad/ — sitting parliamentarians as PEPs; dedup/validation.

### in-rolls/indian-politician-bios — ✓ secondary
- https://github.com/in-rolls/indian-politician-bios — bios corpus for office-history + name-variant mining.

---

## Entity resolution — unique-ID strategy

- **TCPD SURF** (https://tcpd.ashoka.edu.in/surf-an-entity-mapping-and-resolution-system-for-indian/) —
  ✓ open-source ER with a similarity metric **built for Indian names** (transliteration variants). Used to
  build the TCPD Incumbents dataset. **Adopt SURF (or its metric) — don't hand-roll fuzzy matching.**
- **Political Career Tracker** (https://lokdhaba.ashoka.edu.in/pct/home.html) — ✓ assigns each individual a
  unique ID and tracks party switching. Seed `person_id` from TCPD/PCT, extend to current + state members.
- **ID model:** canonical `person_id` ↔ many `source_ref`s (sansad_id, myneta_candidate_id, tcpd_surf_id,
  ecourts_cnr). Keep every native ID; never collapse them. See `entity-resolution.md`.

## Party affiliation & "why they switched" — ⚠ partially open

- **Per-term affiliation:** ✓ derivable from each election/affidavit row; diff across terms → switch events.
- **"When & why" / anti-defection:** ⚠ no clean structured source. Speaker/Chairman 10th-Schedule orders are
  inconsistent PDFs. Strategy: auto-detect switch events structurally; enrich "why" as **sourced narrative**
  (news/Wikidata/Wikipedia), clearly labelled *reported*, not adjudicated.
- **PRS / Rajya Sabha official API:** ⚠ unconfirmed — follow-up probe.

## Legal & ethical (resolve before any public launch)

1. **MyNeta non-commercial license** — biggest gate.
2. **DPDP Act 2023** — republishing criminal-case data carries defamation / RTBF exposure.
3. **Cases are mostly pending/alleged** — always show pending-vs-convicted, cite source, never assert guilt.
4. **Provenance everywhere** — every datapoint links to its source.

## Verification provenance

Deep-research run: 5 angles · 20 sources fetched · 90 claims · 25 adversarially verified (3-vote) ·
21 confirmed · 4 killed. Killed (false): "data.gov.in has no political datasets", "sansad.in has no IDs/API",
"MyNeta is an unmodified ECI mirror", "eCourts has zero programmatic access".
