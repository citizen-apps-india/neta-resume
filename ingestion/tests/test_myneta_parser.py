"""Parser tests against a saved MyNeta candidate fixture (no network)."""

from pathlib import Path

from neta_ingest.sources.myneta.parser import parse_candidate

FIXTURES = Path(__file__).parent / "fixtures"


def _candidate():
    html = (FIXTURES / "myneta_candidate_5395.html").read_text(encoding="utf-8", errors="ignore")
    return parse_candidate(html, candidate_id="5395")


def test_header_fields():
    c = _candidate()
    assert c.name == "GODAM NAGESH"
    assert c.party == "BJP"
    assert c.constituency == "ADILABAD"
    assert c.state == "TELANGANA"
    assert c.age == 59
    assert "Post Graduate" in (c.education or "")


def test_assets_parsed_to_integer_rupees():
    c = _candidate()
    assert c.total_assets == 30916833       # Rs 3,09,16,833
    assert c.total_liabilities == 2901575   # Rs 29,01,575


def test_criminal_case_extracted():
    c = _candidate()
    assert len(c.criminal_cases) == 1
    case = c.criminal_cases[0]
    assert case.fir_number and "158/2024" in case.fir_number
    assert "188" in case.raw_sections
    assert case.is_convicted is False
    assert case.charges_framed is False
    # Structured sections include the IPC charges and the electoral RPA 125 (from "R.P. Act").
    assert ("IPC", "188") in case.sections
    assert ("RPA", "125") in case.sections


def test_multi_case_candidate_5083():
    """Regression: table-based parse must catch all cases despite varied FIR/case-number formats."""
    html = (FIXTURES / "myneta_candidate_5083.html").read_text(encoding="utf-8", errors="ignore")
    c = parse_candidate(html, candidate_id="5083")
    assert len(c.criminal_cases) == 13          # winners-list count for this MP
    # Most cases carry structured sections (a few affidavit rows legitimately omit section numbers).
    assert sum(1 for case in c.criminal_cases if case.sections) >= 11
    assert any(("IPC", "120B") in case.sections for case in c.criminal_cases)
