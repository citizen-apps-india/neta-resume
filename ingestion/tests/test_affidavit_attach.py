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
    # unrelated names score below the match gate. (JW's floor is higher than difflib's, but 0.80 is the
    # lowest threshold any caller uses, so staying under it — not under 0.5 — is what matters.)
    assert name_score("Rahul Gandhi", "Narendra Modi") < 0.80


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


def test_name_score_subset_absorbs_word_order():
    # reordered multi-token name -> token-subset tier (>=2 shared), order-independent
    assert name_score("Karunanidhi Muthuvel", "Muthuvel Karunanidhi") >= 0.90


def test_name_score_fuzzy_catches_romanization_variants():
    # Jaro-Winkler fuzzy tier (single-token, <2 shared tokens) lifts true romanized spelling variants
    # over the same-constituency 0.80 gate — including ones the old difflib ratio missed
    # ("Anbarasan"/"Anbazhagan" was 0.74 under difflib, now ~0.90).
    assert name_score("Anbarasan", "Anbazhagan") >= 0.80
    assert name_score("Rajendran", "Rajender") >= 0.80
    assert name_score("Krishnamurthy", "Krishnamoorthy") >= 0.80


def test_name_score_fuzzy_rejects_distinct_names():
    # Clearly different people stay well below every match gate (0.80 / 0.88 / 0.90).
    assert name_score("Ramesh Kumar", "Suresh Yadav") < 0.80
    assert name_score("Anbarasan", "Palaniswami") < 0.80


def test_name_score_shared_surname_stays_below_strict_gates():
    # Different people sharing ONE surname (dynastic namesakes) fall to the fuzzy tier (subset needs
    # >=2 shared tokens). JW's prefix weighting lifts them, but they must stay below the strict global
    # (0.90) and attendance (0.88) gates; the same-const 0.80 path is guarded by age corroboration.
    s = name_score("Gandhi Rahul", "Gandhi Sonia")
    assert s < 0.88
