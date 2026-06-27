"""Party-switch pipeline: structural detection + narrative enrichment.

Steps:
  1. For each person, order office_term rows by start_date; diff party_id across consecutive terms.
  2. Each change -> party_switch_event(from_party, to_party, event_date, detected_from='term_diff')
     and maintain party_affiliation rows (joined/left dates, is_current).
  3. Narrative enrichment ("why") is a SEPARATE low-trust pass: pull from news/Wikidata, attach as
     party_switch_event.narrative + narrative_source_ref_id (trust_tier=3), labelled "reported" in UI.

The structural step is high-trust; the "why" is explicitly reported, never adjudicated.
"""

from __future__ import annotations


def run() -> None:
    raise NotImplementedError(
        "party_switch scaffolded. Step 1 (term-diff detection) is pure SQL/Python over office_term; "
        "implement after roster+resolve produce multi-cycle office_term rows (Phase 3/4)."
    )
