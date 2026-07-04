"""Cross-house stitcher scoring: each band + each veto (pure function, no DB)."""

from neta_core.transform.names import normalize_name

from neta_ingest.pipelines.identity.stitch_score import score_person_pair


def P(name, *, birth=None, state=None, rel=None, gender=None, native=None, parties=()):
    return {
        "display_name": name, "normalized_name": normalize_name(name),
        "birth_year": birth, "home_state": state, "relative_name": rel,
        "gender": gender, "native_name": native, "party_ids": parties,
    }


def test_auto_merge_needs_multiple_corroborating_signals():
    a = P("RAM KUMAR SINGH", birth=1970, state="BIHAR", rel="Shyam Singh", parties=(5,))
    b = P("RAM KUMAR SINGH", birth=1970, state="BIHAR", rel="Shyam Singh", parties=(5,))
    score, band, ev = score_person_pair(a, b)
    assert band == "auto_merge"
    assert score >= 0.92
    assert ev["corroborating"] >= 2


def test_name_alone_never_auto_merges():
    # A lone perfect name (two same-name politicians, no other signals) must not auto-merge.
    score, band, _ = score_person_pair(P("RAM KUMAR SINGH"), P("RAM KUMAR SINGH"))
    assert band == "reject"          # 0.35 < reject floor
    assert band != "auto_merge"


def test_review_band_when_strong_but_not_certain():
    a = P("SUNITA DEVI", birth=1980, state="BIHAR", rel="Ram Devi")
    b = P("SUNITA DEVI", birth=1980, state="BIHAR", rel="Ram Devi")
    score, band, _ = score_person_pair(a, b)
    assert band == "review"
    assert 0.80 <= score < 0.92


def test_veto_gender_mismatch():
    a = P("RAM KUMAR SINGH", birth=1970, state="BIHAR", rel="Shyam Singh", gender="M", parties=(5,))
    b = P("RAM KUMAR SINGH", birth=1970, state="BIHAR", rel="Shyam Singh", gender="F", parties=(5,))
    _, band, ev = score_person_pair(a, b)
    assert band == "reject"
    assert "gender_mismatch" in ev["vetoes"]


def test_veto_birth_year_gap():
    a = P("RAM KUMAR SINGH", birth=1950, state="BIHAR", rel="Shyam Singh")
    b = P("RAM KUMAR SINGH", birth=1985, state="BIHAR", rel="Shyam Singh")
    _, band, ev = score_person_pair(a, b)
    assert band == "reject"
    assert "birth_year_gap" in ev["vetoes"]


def test_veto_relative_mismatch():
    # Same common name, but different fathers -> two different people.
    a = P("RAM KUMAR SINGH", birth=1970, rel="Shyam Singh")
    b = P("RAM KUMAR SINGH", birth=1970, rel="Mohan Prasad Yadav")
    _, band, ev = score_person_pair(a, b)
    assert band == "reject"
    assert "relative_mismatch" in ev["vetoes"]


def test_name_below_floor_rejected():
    _, band, _ = score_person_pair(P("RAM KUMAR SINGH"), P("GEETA BEN PATEL"))
    assert band == "reject"
