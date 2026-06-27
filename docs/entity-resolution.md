# Entity Resolution

**Goal:** one canonical `person.id` linking `sansad.in` roster ↔ MyNeta candidate ↔ TCPD/SURF ID ↔ court
records, robust to Indian-name transliteration variants. This is the **highest-risk correctness component** —
a wrong merge attaches someone else's assets/cases to a person's resume.

## Canonical ID strategy

- `person.id` is an internal surrogate, **never** a source's native ID. Source identities live in
  `source_ref(source_id, native_id, person_id)`.
- **Seed from TCPD/SURF first.** SURF / LokDhaba / Political Career Tracker already assign unique IDs and
  track party switching across elections. Where a `tcpd_surf_id` exists it anchors the `person` row — a
  high-quality backbone before any fuzzy matching.

## Pipeline (`ingestion/neta_ingest/resolve/`)

1. **Normalize** (`transform/names.py`) — transliteration normalization (Devanagari↔Latin), lowercasing,
   honorific stripping (Dr./Shri/Smt/Adv), initial expansion, token sort → `person.normalized_name`; store
   every raw spelling in `person_name_variant`.
2. **Blocking** (`resolve/blocking.py`) — cheap candidate-pair generation: block on (state/constituency),
   (party), (birth_year ±1), `pg_trgm` similarity on normalized name. Avoids O(n²).
3. **Similarity / SURF** (`resolve/surf.py`) — plug in TCPD **SURF**'s name-similarity metric (built for
   Indian name variants) as the primary string scorer; combine with structured signals (same
   constituency+cycle, overlapping party history, age) into a weighted score.
4. **Match decision** (`resolve/match.py`) — three bands: auto-merge above high threshold, auto-reject below
   low, **review queue** (`er_candidate`) in between. Hobby-scale → a small manual review list protects precision.
5. **Link** (`resolve/link.py`) — set `source_ref.person_id`. Reversible (just an FK); re-runs idempotent.
   Keep an `er_decision` audit (signals fired, score, rule version) so merges are explainable.

## Cross-source linkage order

- TCPD seeds `person` + `tcpd_surf_id`.
- sansad roster → person (exact constituency+cycle where possible, else SURF).
- MyNeta candidate → person on (election_cycle, constituency, normalized name) — strong, both election-partitioned.
- Court records → linked via the person already matched through MyNeta (cases declared in affidavits inherit
  `person_id`), then enriched live by `cnr_number` against bharat-courts.
