# Criminal-Case Severity Rubric

Severity is **derived**, **data-driven**, and **versioned** — not hard-coded in app logic.

## Rubric (based on ADR's "serious criminal" definition)

ADR classifies an offence as **serious** when it carries a maximum punishment of **5 years or more**, plus a
curated list (non-bailable, electoral offences, offences against women, corruption, crimes carrying
life/death). Neta-Resume extends this to three tiers:

| Tier | Definition | Examples (IPC → BNS) |
|---|---|---|
| **heinous** | life-imprisonment / death eligible, or grave offences against women | murder 302→103, rape 376→64, kidnapping-for-ransom 364A→140 |
| **serious** | ADR rule: max punishment ≥ 5 years, non-bailable, corruption, electoral offences | … |
| **minor** | everything else (bailable, < 5 years) | defamation, unlawful assembly (low grade) |

## Where the logic lives

1. **Catalog table `legal_section`** holds `base_severity`, `max_punishment_years`, `is_cognizable` per
   IPC/BNS section. Seeded from `db/seeds/ipc_bns_sections.sql` + `db/seeds/severity_rules.sql`.
2. **Section parsing** — `ingestion/neta_ingest/transform/sections.py` parses `raw_section_text`
   ("u/s 302/34 IPC", "BNS 103") into `(code_system, section_number)` and resolves to `legal_section.id`.
3. **IPC → BNS transition** (the legal code changed mid-2024; cases span both) is handled via the crosswalk
   columns `ipc_equivalent` / `bns_equivalent`, so a case under either code maps to the same severity.
4. **Case-level rollup** — a case's `severity` = the **max** severity across its charges (one heinous charge
   → heinous case). Stamped with `severity_rule_version` for auditable re-classification.

The FastAPI read layer **never classifies at request time** — it reads the already-computed `severity`.

## Why table-driven, not code constants

ADR periodically revises its serious-crime list, and the IPC→BNS migration means the section catalog must be
editable, versioned data (migration/seed), not baked into Python. Re-running the classifier with a new
`severity_rule_version` reclassifies historical cases reproducibly.

## Display rules (legal safety)

- Always show **pending vs convicted** status and the **filed year**.
- Never assert guilt; cases are mostly **alleged**.
- Always render the **source link** (affidavit page / court CNR).
