# Data Licensing & Ethics

Neta-Resume is a **non-commercial / hobby** project. The application code is MIT (see `LICENSE`); the **data**
is governed by each upstream source's terms (see `NOTICE`).

## Hard constraints

| Source | Constraint | Implication |
|---|---|---|
| MyNeta / ADR | **Non-commercial use only**; no bulk CSV | Keep the project non-commercial. Do not redistribute bulk data. Attribute ADR. Scrape politely (cache + rate-limit). |
| ECI affidavits | Public filing | Canonical; use for verification. |
| sansad.in | Official public roster | Attribute Digital Sansad. |
| TCPD (SURF/LokDhaba/PCT) | Academic | Cite TCPD-IPD where IDs/data used. |
| data.gov.in | GODL-India | Attribution per GODL. |
| eCourts / bharat-courts | Court records public; access gated | Best-effort enrichment; respect rate limits / no CAPTCHA circumvention abuse. |

## DPDP Act 2023

India's Digital Personal Data Protection Act applies. Affidavit data is filed for **electoral transparency**
(a strong public-interest basis), but republishing **criminal-case** data carries defamation / right-to-be-
forgotten exposure. Mitigations baked into the design:

1. **Pending vs convicted** is always shown; the site never asserts guilt.
2. **Provenance on every fact** — each datapoint links to its affidavit page / court CNR for dispute-resilience.
3. **Reported narratives** (e.g. *why* someone switched parties) are explicitly labelled as reported, not
   adjudicated, and carry a lower `trust_tier` source.
4. The repo is **private** until data-handling and framing are reviewed.

## Going commercial later

Would require, at minimum: ADR permission or independent sourcing of affidavits from ECI PDFs; a fresh review
of DPDP obligations; and a takedown/correction process.
