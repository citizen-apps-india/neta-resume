"""PRS MP Track parser tests against saved fixtures (no network).

Guards the scorecard scrape: the activity counts live on the listing card, the reporting window + the
member's own attendance on the profile. All three parse from server-rendered HTML.
"""

from datetime import date
from pathlib import Path

from neta_sources.prs.client import (
    parse_attendance,
    parse_debates,
    parse_listing,
    parse_questions,
    parse_report_period,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _listing() -> str:
    return (FIXTURES / "prs_mptrack_ls_listing.html").read_text(encoding="utf-8", errors="ignore")


def _profile() -> str:
    return (FIXTURES / "prs_mptrack_profile_tharoor.html").read_text(encoding="utf-8", errors="ignore")


def test_listing_parses_all_cards_with_counts():
    members = parse_listing(_listing(), "ls")
    assert len(members) == 9                       # 9 cards per page
    # every card carries all three cumulative counts
    assert all(m.questions is not None and m.debates is not None
               and m.private_member_bills is not None for m in members)


def test_listing_card_values():
    by_slug = {m.slug: m for m in parse_listing(_listing(), "ls")}
    m = by_slug["abhay-kumar-sinha"]
    assert m.name == "Abhay Kumar Sinha"
    assert (m.debates, m.questions, m.private_member_bills) == (49, 44, 0)
    assert m.profile_url.endswith("/mptrack/18th-lok-sabha/abhay-kumar-sinha")


def test_report_period():
    assert parse_report_period(_profile()) == (date(2024, 6, 24), date(2026, 4, 18))


def test_profile_attendance():
    assert parse_attendance(_profile()) == 88.0


def test_report_period_absent_returns_none():
    assert parse_report_period("<html>no period here</html>") is None


def test_profile_questions_parse_fully():
    qs = parse_questions(_profile())
    assert len(qs) == 119                          # matches the PRS scorecard's question count exactly
    assert len({q.question_ref for q in qs}) == 119  # refs unique -> idempotent upsert key
    assert all(q.question_type in {"Starred", "Unstarred"} for q in qs)


def test_profile_question_fields():
    by_ref = {q.question_ref: q for q in parse_questions(_profile())}
    q = by_ref["187-AU6358"]                        # session-scoped annex id from the PDF path
    assert q.subject == "Norms for Setting up of New Airports"
    assert q.ministry == "Civil Aviation"
    assert q.question_type == "Unstarred"
    assert q.asked_date == date(2026, 4, 2)
    assert q.document_url.startswith("https://sansad.in/getFile/loksabhaquestions/annex/187/AU6358_")


def test_profile_debates_parse_fully():
    ds = parse_debates(_profile())
    assert len(ds) == 33                            # matches the PRS scorecard's debate count exactly
    assert len({d.debate_ref for d in ds}) == 33
    assert all(d.debate_date is not None and d.title for d in ds)


def test_questions_and_debates_absent_return_empty():
    assert parse_questions("<html>nothing</html>") == []
    assert parse_debates("<html>nothing</html>") == []
