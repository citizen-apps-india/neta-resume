"""Pure tests for `derive_metrics` — no database. See PHASE3-SPEC.md §2.5/§2.6."""

from __future__ import annotations

from neta_api.services.eci_files import derive_metrics


def _stage(electors: int, *, computed: bool = False, approx: bool = False, note: str | None = None) -> dict:
    return {"electors": electors, "computed": computed, "approx": approx, "note": note}


def test_draft_left_off_formula() -> None:
    stages = {"before": _stage(100), "draft": _stage(80)}
    metrics = derive_metrics(stages, "sir")
    assert metrics["draft_left_off"] == {
        "value": 20.0,
        "count": 20,
        "base": 100,
        "computed": False,
        "approx": False,
        "noted": False,
    }


def test_net_change_formula() -> None:
    stages = {"before": _stage(100), "final": _stage(90)}
    metrics = derive_metrics(stages, "sir")
    assert metrics["net_change"] == {
        "value": -10.0,
        "count": -10,
        "base": 100,
        "computed": False,
        "approx": False,
        "noted": False,
    }


def test_appeals_filed_formula() -> None:
    stages = {"appeals_filed": _stage(10), "final": _stage(100)}
    metrics = derive_metrics(stages, "sir")
    assert metrics["appeals_filed"] == {
        "value": 10.0,
        "count": 10,
        "base": 100,
        "computed": False,
        "approx": False,
        "noted": False,
    }


def test_net_change_is_signed_positive_for_a_rise() -> None:
    stages = {"before": _stage(100), "final": _stage(110)}
    metrics = derive_metrics(stages, "sir")
    assert metrics["net_change"]["value"] == 10.0
    assert metrics["net_change"]["count"] == 10


def test_draft_left_off_is_null_when_a_stage_is_missing() -> None:
    stages = {"before": _stage(100)}
    metrics = derive_metrics(stages, "sir")
    assert metrics["draft_left_off"] is None


def test_net_change_is_null_when_final_is_missing() -> None:
    stages = {"before": _stage(100), "draft": _stage(80)}
    metrics = derive_metrics(stages, "sir")
    assert metrics["net_change"] is None


def test_appeals_filed_is_null_when_appeals_are_missing() -> None:
    stages = {"before": _stage(100), "final": _stage(90)}
    metrics = derive_metrics(stages, "sir")
    assert metrics["appeals_filed"] is None


def test_all_metrics_are_null_for_special_revision() -> None:
    stages = {
        "before": _stage(100),
        "draft": _stage(80),
        "final": _stage(90),
        "appeals_filed": _stage(5),
    }
    metrics = derive_metrics(stages, "special_revision")
    assert metrics == {"draft_left_off": None, "net_change": None, "appeals_filed": None}


def test_all_metrics_are_null_when_exercise_is_none() -> None:
    stages = {"before": _stage(100), "draft": _stage(80), "final": _stage(90)}
    metrics = derive_metrics(stages, None)
    assert metrics == {"draft_left_off": None, "net_change": None, "appeals_filed": None}


def test_computed_propagates_from_either_contributing_stage() -> None:
    stages = {"before": _stage(100, computed=True), "draft": _stage(80)}
    metrics = derive_metrics(stages, "sir")
    assert metrics["draft_left_off"]["computed"] is True

    stages = {"before": _stage(100), "draft": _stage(80, computed=True)}
    metrics = derive_metrics(stages, "sir")
    assert metrics["draft_left_off"]["computed"] is True


def test_approx_propagates_from_either_contributing_stage() -> None:
    stages = {"before": _stage(100), "draft": _stage(80, approx=True)}
    metrics = derive_metrics(stages, "sir")
    assert metrics["draft_left_off"]["approx"] is True


def test_noted_is_true_when_either_contributing_stage_has_a_note() -> None:
    stages = {"before": _stage(100), "final": _stage(90, note="a caveat")}
    metrics = derive_metrics(stages, "sir")
    assert metrics["net_change"]["noted"] is True


def test_noted_is_false_when_neither_contributing_stage_has_a_note() -> None:
    stages = {"before": _stage(100), "final": _stage(90)}
    metrics = derive_metrics(stages, "sir")
    assert metrics["net_change"]["noted"] is False


def test_value_is_rounded_to_two_decimal_places() -> None:
    stages = {"before": _stage(78969844), "draft": _stage(72400000)}
    metrics = derive_metrics(stages, "sir")
    assert metrics["draft_left_off"]["value"] == 8.32
    assert metrics["draft_left_off"]["count"] == 6569844
