"""Tests for the shared person<->candidate matching used by enrich-missing and historical-lookup."""

from neta_ingest.pipelines.identity.affidavit_attach import best_match, cycle_year, name_score, name_tokens


def test_cycle_year():
    assert cycle_year("LS2019") == 2019
    assert cycle_year("LS2009") == 2009


def test_name_tokens_drops_titles_and_initials():
    assert name_tokens("Dr. Shashi Tharoor") == {"shashi", "tharoor"}
    assert "adv" not in name_tokens("Adv. P. Chidambaram")


def test_name_score_exact_and_subset():
    # exact normalized match
    assert name_score("Shashi Tharoor", "Dr. Shashi Tharoor", normalized_name="shashi tharoor") == 1.0
    # token-subset (honorific/initial differences) scores high without an exact normalized match
    assert name_score("Rahul Gandhi", "Shri Rahul Gandhi") >= 0.90
    # unrelated names score low
    assert name_score("Rahul Gandhi", "Narendra Modi") < 0.5


def test_best_match_picks_top_above_threshold():
    cands = [("11", "Narendra Modi"), ("22", "Rahul Gandhi"), ("33", "Amit Shah")]
    cid, score, ambiguous = best_match(cands, "Rahul Gandhi", "rahul gandhi", threshold=0.85)
    assert cid == "22"
    assert score >= 0.9
    assert ambiguous is False


def test_best_match_flags_ambiguous_namesakes():
    # Two different candidates with the same name -> ambiguous, must not auto-pick.
    cands = [("100", "Ram Kumar"), ("200", "Ram Kumar")]
    cid, score, ambiguous = best_match(cands, "Ram Kumar", "kumar ram", threshold=0.85)
    assert ambiguous is True


def test_best_match_returns_none_below_threshold():
    cands = [("1", "Some Other Person")]
    cid, score, ambiguous = best_match(cands, "Rahul Gandhi", "rahul gandhi", threshold=0.85)
    assert cid is None
