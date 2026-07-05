"""Pure person-pair scoring for the cross-house identity stitcher.

Blends name + relative + birth-year + home-state + party-lineage + gender + native-name into a 0..1
score, a decision band, and a per-signal evidence dict. Precision-first:
  * a lone strong NAME can never auto-merge — the weights make ≥2 corroborating signals necessary to
    clear the auto-merge floor (so two same-name politicians in different houses aren't fused);
  * confident CONFLICTS on relative / birth-year / gender VETO the pair to 'reject'.

A person dict carries: display_name, normalized_name, birth_year, home_state, relative_name, gender,
native_name, party_ids (iterable). Missing signals are neutral (neither help nor veto).
"""

from __future__ import annotations

from neta_core.transform.names import normalize_name, phonetic_key

from neta_ingest.pipelines.identity.affidavit_attach import name_score

RULE_VERSION = "stitch-v2"   # v2: phonetic name tier (re-opens prior rejects for re-scoring once)

# Contributions sum to 1.0 when every signal agrees perfectly.
W_NAME, W_REL, W_BIRTH, W_STATE, W_PARTY, W_GENDER, W_NATIVE = 0.35, 0.25, 0.15, 0.10, 0.08, 0.04, 0.03

NAME_FLOOR = 0.85          # below this the pair is not a real candidate
PHONETIC_NAME_FLOOR = 0.88  # a metaphone-equal below-floor name is lifted to here (clears floor, < token-subset)
REL_MATCH = 0.85           # relatives this similar corroborate
REL_VETO = 0.50            # both relatives known and this dissimilar -> veto
AUTO_MERGE_SCORE = 0.92
AUTO_MERGE_MIN_CORROBORATING = 2   # non-name signals that must positively agree to auto-merge
REJECT_SCORE = 0.80


def _known(v) -> bool:
    return v is not None and v != ""


def score_person_pair(a: dict, b: dict) -> tuple[float, str, dict]:
    """Return (score 0..1, band 'auto_merge'|'review'|'reject', evidence dict)."""
    ev: dict = {}
    vetoes: list[str] = []

    name_sim = name_score(a["display_name"], b["display_name"], a.get("normalized_name"))
    # Phonetic tier (stitcher-only): lift a below-floor name if the two are metaphone-equal (same sound,
    # different spelling). This never adds a corroborating signal, so a phonetic name still needs >=2 hard
    # signals to auto-merge — and vetoes still override.
    if name_sim < NAME_FLOOR:
        pa, pb = phonetic_key(a["display_name"]), phonetic_key(b["display_name"])
        if pa and pa == pb:
            ev["phonetic"] = {"a": pa, "b": pb, "boosted_from": round(name_sim, 4)}
            name_sim = max(name_sim, PHONETIC_NAME_FLOOR)
    ev["name"] = round(name_sim, 4)
    if name_sim < NAME_FLOOR:
        ev["gate"] = "name_floor"
        return 0.0, "reject", ev

    score = W_NAME * name_sim
    corroborating = 0

    ra, rb = a.get("relative_name"), b.get("relative_name")
    if _known(ra) and _known(rb):
        rel_sim = name_score(ra, rb, normalize_name(ra))   # exact (normalized) relative -> 1.0
        ev["relative"] = {"a": ra, "b": rb, "sim": round(rel_sim, 4)}
        if rel_sim >= REL_MATCH:
            score += W_REL * rel_sim
            corroborating += 1
        elif rel_sim < REL_VETO:
            vetoes.append("relative_mismatch")
    else:
        ev["relative"] = None

    ba, bb = a.get("birth_year"), b.get("birth_year")
    if _known(ba) and _known(bb):
        d = abs(int(ba) - int(bb))
        ev["birth"] = {"a": ba, "b": bb, "delta": d}
        if d <= 1:
            score += W_BIRTH
            corroborating += 1
        elif d <= 3:
            score += W_BIRTH * 0.5
        else:
            vetoes.append("birth_year_gap")
    else:
        ev["birth"] = None

    sa, sb = a.get("home_state"), b.get("home_state")
    if _known(sa) and _known(sb):
        match = sa.strip().upper() == sb.strip().upper()
        ev["state"] = {"a": sa, "b": sb, "match": match}
        if match:
            score += W_STATE
            corroborating += 1

    shared = set(a.get("party_ids") or ()) & set(b.get("party_ids") or ())
    if shared:
        score += W_PARTY
        corroborating += 1
        ev["party"] = {"shared": sorted(shared)}

    ga, gb = a.get("gender"), b.get("gender")
    if _known(ga) and _known(gb):
        if ga == gb:
            score += W_GENDER
            corroborating += 1
        else:
            vetoes.append("gender_mismatch")

    na, nb = a.get("native_name"), b.get("native_name")
    if _known(na) and _known(nb) and na.strip() == nb.strip():
        score += W_NATIVE
        corroborating += 1

    score = min(score, 1.0)
    ev["corroborating"] = corroborating
    ev["vetoes"] = vetoes

    # `gate` records why the pair landed where it did (for the recall audit's near-miss listing).
    if vetoes:
        band, ev["gate"] = "reject", "veto:" + vetoes[0]
    elif score >= AUTO_MERGE_SCORE and corroborating >= AUTO_MERGE_MIN_CORROBORATING:
        band, ev["gate"] = "auto_merge", "auto_merge"
    elif score >= AUTO_MERGE_SCORE:  # score high enough but too few corroborating signals
        band, ev["gate"] = "review", "insufficient_corroborating"
    elif score < REJECT_SCORE:
        band, ev["gate"] = "reject", "score<reject"
    else:
        band, ev["gate"] = "review", "review"
    return round(score, 4), band, ev
