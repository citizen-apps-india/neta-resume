"""Shared logic for attaching a MyNeta candidate's affidavit + criminal data to an EXISTING person.

Two pipelines use this:
  - enrich_missing_affidavits — fills current-roster (LS18) members MyNeta omits from its winners list
  - historical_lookup         — backfills a current MP's PAST-cycle candidacies (even losses/seat changes)

The invariant in both: we never create a new person here. We resolve the right MyNeta candidate, then
write its facts onto a person we already have, with a MyNeta source_ref for provenance. Idempotent on
that source_ref (delete this source_ref's derived facts, re-insert). Cycle/filed-year are parameters so
the same writer serves LS2024, LS2019, LS2014, LS2009.
"""

from __future__ import annotations

import difflib
import re

from sqlalchemy import text

from neta_ingest.config import settings
from neta_ingest.sources.myneta import client as myneta
from neta_ingest.sources.myneta.parser import ParsedCandidate
from neta_ingest.transform.names import normalize_name
from neta_ingest.transform.sections import rollup_severity

_TITLES = {"dr", "shri", "smt", "kumari", "km", "adv", "prof", "mr", "mrs", "ms", "com", "chh",
           "maharaj", "alias", "thiru", "selvi", "md", "mohd", "capt", "col", "justice", "ku"}


def cycle_year(cycle: str) -> int:
    """The 4-digit year embedded in an election-cycle code, e.g. 'LS2019' -> 2019."""
    m = re.search(r"(\d{4})", cycle)
    if not m:
        raise ValueError(f"cannot derive filed year from cycle {cycle!r}")
    return int(m.group(1))


def name_tokens(s: str) -> set[str]:
    """Meaningful (de-titled) lowercase tokens of a name, for subset/overlap matching."""
    return {t for t in re.sub(r"[^a-z ]", " ", s.lower()).split() if len(t) > 1 and t not in _TITLES}


def strip_const(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def resolve_constituency(const_map: dict[str, str], stripped: dict[str, str], constituency: str) -> str | None:
    """Map a roster constituency name to a MyNeta constituency_id (exact, stripped, then fuzzy)."""
    norm = myneta._norm_const(constituency)
    if norm in const_map:
        return const_map[norm]
    if strip_const(norm) in stripped:
        return stripped[strip_const(norm)]
    close = difflib.get_close_matches(norm, const_map.keys(), n=1, cutoff=0.84)
    return const_map[close[0]] if close else None


def name_score(display_name: str, cand_name: str, normalized_name: str | None = None) -> float:
    """Similarity in [0,1] between a person and a candidate name.

    1.00 exact normalized match · 0.90 token-subset with >=2 shared meaningful tokens ·
    else the de-titled fuzzy ratio. Honorifics/initials/word-order are absorbed by tokenization.
    """
    if normalized_name and normalize_name(cand_name) == normalized_name:
        return 1.0
    want = name_tokens(display_name)
    have = name_tokens(cand_name)
    if not want or not have:
        return 0.0
    if (want <= have or have <= want) and len(want & have) >= 2:
        return 0.90
    return difflib.SequenceMatcher(None, " ".join(sorted(want)), " ".join(sorted(have))).ratio()


def best_match(cands: list[tuple[str, str]], display_name: str, normalized_name: str | None,
               *, threshold: float) -> tuple[str | None, float, bool]:
    """Best (candidate_id, score, ambiguous) over (cand_id, name) rows.

    `ambiguous` is True when two *different* candidates tie near the top — a signal to route to a
    review queue rather than auto-write (these are criminal records: precision over recall).
    """
    scored: list[tuple[float, str]] = []
    for cand_id, cand_name in cands:
        scored.append((name_score(display_name, cand_name, normalized_name), cand_id))
    if not scored:
        return None, 0.0, False
    scored.sort(reverse=True)
    top_score, top_id = scored[0]
    if top_score < threshold:
        return None, top_score, False
    runner = next((s for s, cid in scored[1:] if cid != top_id), 0.0)
    ambiguous = runner >= top_score - 0.05 and runner >= threshold
    return top_id, top_score, ambiguous


def _scalar(s, sql: str, **p):
    return s.execute(text(sql), p).scalar()


def write_affidavit(s, c: ParsedCandidate, person_id: int, candidate_id: str, raw_rel: str,
                    *, house_id: int, term_cycle_id: int, cycle: str) -> int:
    """Attach a parsed candidate's affidavit + criminal cases onto an existing person. Idempotent.

    Returns the affidavit id. Provenance: a MyNeta source_ref (source_id, candidate_id) pinned to the
    cached raw page, linked to person_id.
    """
    filed_year = cycle_year(cycle)
    source_id = _scalar(s, "SELECT id FROM source WHERE code='myneta'")
    source_url = myneta.candidate_url(candidate_id, cycle)
    source_ref_id = _scalar(
        s,
        """
        INSERT INTO source_ref (source_id, native_id, native_url, raw_name, raw_payload_ref, person_id)
        VALUES (:sid, :nid, :url, :name, :raw, :pid)
        ON CONFLICT (source_id, native_id) DO UPDATE
          SET native_url = EXCLUDED.native_url, person_id = EXCLUDED.person_id, fetched_at = now()
        RETURNING id
        """,
        sid=source_id, nid=myneta.native_id(cycle, candidate_id), url=source_url, name=c.name,
        raw=raw_rel, pid=person_id,
    )
    if c.age:
        s.execute(text("UPDATE person SET birth_year = COALESCE(birth_year, :by) WHERE id = :pid"),
                  {"by": filed_year - c.age, "pid": person_id})

    # Idempotent: clear this source_ref's prior derived facts, then re-insert.
    s.execute(text("DELETE FROM case_charge WHERE criminal_case_id IN "
                   "(SELECT id FROM criminal_case WHERE source_ref_id=:sr)"), {"sr": source_ref_id})
    for tbl in ("criminal_case", "affidavit"):
        s.execute(text(f"DELETE FROM {tbl} WHERE source_ref_id=:sr"), {"sr": source_ref_id})

    affidavit_id = _scalar(
        s,
        """
        INSERT INTO affidavit
          (person_id, source_ref_id, election_cycle, house_id, filed_year, age, education,
           total_assets, total_liabilities, movable_assets, immovable_assets, self_income, income_year, raw_url)
        VALUES (:pid,:sr,:cycle,:hid,:fy,:age,:edu,:assets,:liab,:mov,:immov,:income,:iyear,:url)
        RETURNING id
        """,
        pid=person_id, sr=source_ref_id, cycle=cycle, hid=house_id, fy=filed_year, age=c.age,
        edu=c.education, assets=c.total_assets, liab=c.total_liabilities, mov=c.movable_assets,
        immov=c.immovable_assets, income=c.self_income, iyear=c.income_year, url=source_url,
    )
    for case in c.criminal_cases:
        severities = [
            _scalar(s, "SELECT base_severity FROM legal_section WHERE code_system=:cs AND section_number=:sn",
                    cs=code, sn=num)
            for code, num in case.sections
        ]
        severity = rollup_severity(severities)
        status = "convicted" if case.is_convicted else ("framed_charges" if case.charges_framed else "pending")
        case_id = _scalar(
            s,
            """
            INSERT INTO criminal_case
              (person_id, affidavit_id, source_ref_id, case_number, court, filed_year, status,
               is_convicted, severity, severity_rule_version, description)
            VALUES (:pid,:aid,:sr,:cn,:court,:fy,:st,:conv,:sev,:ver,:desc) RETURNING id
            """,
            pid=person_id, aid=affidavit_id, sr=source_ref_id, cn=case.fir_number, court=case.court,
            fy=filed_year, st=status, conv=case.is_convicted, sev=severity,
            ver=settings.severity_rule_version, desc=case.raw_sections,
        )
        for code, num in case.sections:
            section_id = _scalar(s, "SELECT id FROM legal_section WHERE code_system=:cs AND section_number=:sn",
                                 cs=code, sn=num)
            s.execute(
                text("INSERT INTO case_charge (criminal_case_id, section_id, raw_section_text) "
                     "VALUES (:cid,:sid,:raw)"),
                {"cid": case_id, "sid": section_id, "raw": f"{code} {num}"},
            )
    return affidavit_id
