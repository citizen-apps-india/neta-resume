"""Criminal-case pipeline: MyNeta declared cases -> criminal_case + case_charge (+ severity).

Steps (idempotent):
  1. Fetch declared cases for (house, cycle) from neta_ingest.sources.myneta.
  2. transform.sections.parse_sections(raw) -> [(code_system, section_number)].
  3. Look up legal_section.base_severity for each; transform.sections.rollup_severity -> case severity.
  4. Upsert criminal_case (stamp settings.severity_rule_version) + case_charge.

Court live-status enrichment (bharat-courts/eCourts) is a SEPARATE later pass keyed on cnr_number.
"""

from __future__ import annotations

from neta_ingest.sources.myneta import client as myneta


def run(house: str = "ls", cycle: str = "LS2024") -> None:
    cases = myneta.fetch_criminal_cases(house=house, cycle=cycle)
    raise NotImplementedError(
        f"criminal pipeline scaffolded for house={house} cycle={cycle}; "
        f"got {len(cases)} case rows from MyNeta. Wire section parse + severity rollup next (Phase 1)."
    )
