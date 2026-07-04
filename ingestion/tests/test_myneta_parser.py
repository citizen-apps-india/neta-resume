"""Parser tests against a saved MyNeta candidate fixture (no network)."""

from pathlib import Path

from neta_sources.myneta.parser import parse_candidate

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


def test_asset_breakdown_and_income():
    c = _candidate()
    assert c.movable_assets == 5024833       # Rs 50,24,833
    assert c.immovable_assets == 25892000    # Rs 2,58,92,000
    # movable + immovable should reconcile to the declared total
    assert c.movable_assets + c.immovable_assets == c.total_assets
    assert c.self_income == 1077415          # latest ITR (2022-23): Rs 10,77,415
    assert c.income_year == 2022


def test_relative_name_extracted():
    # MyNeta prints the generic "S/o|D/o|W/o: Late Godam Rama Rao Age: 59" label — capture the name,
    # strip the "Late" honorific, and leave relation_type unknown (the label doesn't disambiguate).
    c = _candidate()
    assert c.relative_name == "Godam Rama Rao"
    assert c.relation_type is None


def test_relative_name_state_fixture():
    # Nitesh Rane's affidavit names his father Narayan Rane (himself a former CM/MP) — the kind of
    # cross-house disambiguation signal this feeds.
    html = (FIXTURES / "myneta_candidate_mh2024_1148.html").read_text(encoding="utf-8", errors="ignore")
    c = parse_candidate(html, candidate_id="1148")
    assert c.relative_name == "Narayan Tatu Rane"


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


def test_ls2014_old_layout_candidate_4916():
    """LS2014 layout: only Serial/IPC/Other columns; the "Other" cell is free-text case metadata.

    Regression for the bug where bare numbers in that cell (case/FIR numbers, years) were mined as
    IPC sections (e.g. a spurious ('IPC', '2009')).
    """
    html = (FIXTURES / "myneta_candidate_ls2014_4916.html").read_text(encoding="utf-8", errors="ignore")
    c = parse_candidate(html, candidate_id="4916")
    assert c.name == "DR. RAMSHANKAR KATHERIA"
    assert c.party == "BJP"
    assert c.constituency == "AGRA"
    assert c.state == "UTTAR PRADESH"
    assert c.total_assets == 14634885
    assert c.total_liabilities == 4035000
    assert len(c.criminal_cases) == 21

    first = c.criminal_cases[0]
    assert ("IPC", "147") in first.sections
    assert ("IPC", "341") in first.sections
    # FIR/Case recovered from the bundled free-text cell.
    assert first.fir_number == "191/2009"
    assert first.case_number == "294/10"

    # No year/serial leaked in as a section anywhere (the core regression).
    all_secs = {num for case in c.criminal_cases for (_code, num) in case.sections}
    assert not (all_secs & {"2009", "2010", "2011", "2012", "2013", "2014"})


def test_ls2009_old_layout_candidate_281():
    """LS2009 layout parses assets + cases; income is legitimately absent (older affidavits)."""
    html = (FIXTURES / "myneta_candidate_ls2009_281.html").read_text(encoding="utf-8", errors="ignore")
    c = parse_candidate(html, candidate_id="281")
    assert c.name == "Ramesh Rathod"
    assert c.total_assets == 3410000
    assert c.total_liabilities == 815241
    assert len(c.criminal_cases) == 2
    assert ("IPC", "353") in c.criminal_cases[0].sections


def test_mh2024_bns_layout_candidate_1148():
    """Maharashtra 2024 (state assembly) layout: the sections column is 'IPC/BNS Sections Applicable'
    and a 'LAW / Section Type' column names IPC vs BNS per row (BNS replaced the IPC on 2024-07-01).
    Regression for the bug where this header didn't match 'IPC Sections' and every case was dropped."""
    html = (FIXTURES / "myneta_candidate_mh2024_1148.html").read_text(encoding="utf-8", errors="ignore")
    c = parse_candidate(html, candidate_id="1148")
    assert c.name == "NITESH NARAYAN RANE"
    assert c.photo_url == "https://myneta.info/images_candidate/Maharashtra2024/1be6fcc03c58186f80b0733e2ac60591d7187535.jpg"
    assert len(c.criminal_cases) == 38                     # cases ARE extracted (was 0 before the fix)
    # Both statutes are coded from the per-row LAW column, not hard-defaulted to IPC.
    all_codes = {code for case in c.criminal_cases for (code, _num) in case.sections}
    assert "BNS" in all_codes
    assert "IPC" in all_codes
