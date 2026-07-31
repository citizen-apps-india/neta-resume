from __future__ import annotations

import pytest
from pydantic import ValidationError

from neta_ingest import runners


def test_digital_sansad_runner_selects_houses(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(runners.ls_roster, "run", lambda: calls.append("ls"))
    monkeypatch.setattr(runners.rajya_sabha, "run", lambda: calls.append("rs"))

    runners.run_digital_sansad_members({})
    runners.run_digital_sansad_members({"house": "rs"})

    assert calls == ["ls", "rs", "rs"]


def test_prs_runner_has_explicit_house_and_operation_controls(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        runners.attendance,
        "run",
        lambda house: calls.append(("attendance", house)),
    )
    monkeypatch.setattr(
        runners.activity,
        "run",
        lambda house: calls.append(("activity", house)),
    )
    monkeypatch.setattr(
        runners.record,
        "run",
        lambda house: calls.append(("record", house)),
    )

    runners.run_prs_parliamentary_record(
        {"houses": ["ls"], "operations": ["activity", "record"]}
    )

    assert calls == [("activity", "ls"), ("record", "ls")]


def test_runner_parameters_reject_unknown_operator_input() -> None:
    with pytest.raises(ValidationError, match="frequesncy"):
        runners.run_worldbank_indicators({"frequesncy": 60})
