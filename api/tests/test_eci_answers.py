"""Pure tests for /eci-files/answers's synthesis, sort and count logic — no database. See
docs/eci-files/PHASE5-SPEC.md section 4.3.
"""

from __future__ import annotations

from datetime import date

from neta_api.services.eci_files import (
    assemble_answer_rows,
    filter_answer_rows,
    finalize_answer_rows,
)


def _row(charge_id: str, d: date | None, *, responses: list | None = None, record: list | None = None) -> dict:
    return {
        "charge": {"id": charge_id, "date": d},
        "also_recorded_as": [],
        "responses": responses or [],
        "record": record or [],
        "related": [],
        "note": None,
        "curated": True,
    }


def test_assemble_answer_rows_adds_an_uncovered_claim() -> None:
    rows = assemble_answer_rows(
        pair_charge_ids=set(),
        also_recorded_ids=set(),
        claim_ids=["claim-1"],
        response_links={},
        unpaired_ids=set(),
    )
    assert len(rows) == 1
    assert rows[0]["charge_id"] == "claim-1"
    assert rows[0]["curated"] is False
    assert rows[0]["response_ids"] == []
    assert rows[0]["record_ids"] == []
    assert rows[0]["related"] == []
    assert rows[0]["note"] is None


def test_assemble_answer_rows_adds_an_uncovered_response_target_with_its_response() -> None:
    rows = assemble_answer_rows(
        pair_charge_ids=set(),
        also_recorded_ids=set(),
        claim_ids=[],
        response_links={"response-1": "target-1"},
        unpaired_ids=set(),
    )
    assert len(rows) == 1
    assert rows[0]["charge_id"] == "target-1"
    assert rows[0]["response_ids"] == ["response-1"]
    assert rows[0]["curated"] is False


def test_assemble_answer_rows_skips_a_charge_id_already_curated() -> None:
    rows = assemble_answer_rows(
        pair_charge_ids={"claim-1"},
        also_recorded_ids=set(),
        claim_ids=["claim-1"],
        response_links={},
        unpaired_ids=set(),
    )
    assert rows == []


def test_assemble_answer_rows_does_not_synthesise_an_also_recorded_as_id() -> None:
    """`also_recorded_as` ids show under a row, not as rows of their own."""
    rows = assemble_answer_rows(
        pair_charge_ids=set(),
        also_recorded_ids={"dup-1"},
        claim_ids=["dup-1"],
        response_links={},
        unpaired_ids=set(),
    )
    assert rows == []


def test_assemble_answer_rows_skips_a_response_target_that_is_an_unpaired_response() -> None:
    rows = assemble_answer_rows(
        pair_charge_ids=set(),
        also_recorded_ids=set(),
        claim_ids=[],
        response_links={"response-1": "target-1"},
        unpaired_ids={"target-1"},
    )
    assert rows == []


def test_assemble_answer_rows_gathers_every_response_pointing_at_the_same_target() -> None:
    rows = assemble_answer_rows(
        pair_charge_ids=set(),
        also_recorded_ids=set(),
        claim_ids=[],
        response_links={"r1": "target-1", "r2": "target-1"},
        unpaired_ids=set(),
    )
    assert len(rows) == 1
    assert sorted(rows[0]["response_ids"]) == ["r1", "r2"]


def test_assemble_answer_rows_never_duplicates_a_charge_seen_as_both_claim_and_response_target() -> None:
    rows = assemble_answer_rows(
        pair_charge_ids=set(),
        also_recorded_ids=set(),
        claim_ids=["shared-1"],
        response_links={"r1": "shared-1"},
        unpaired_ids=set(),
    )
    assert len(rows) == 1
    assert rows[0]["response_ids"] == ["r1"]


def test_finalize_answer_rows_orders_charge_date_descending_then_id() -> None:
    rows = [
        _row("b", date(2026, 1, 1)),
        _row("a", date(2026, 6, 1)),
        _row("c", None),
        _row("d", date(2026, 6, 1)),
    ]
    ordered, _ = finalize_answer_rows(rows)
    assert [r["charge"]["id"] for r in ordered] == ["a", "d", "b", "c"]


def test_finalize_answer_rows_counts() -> None:
    rows = [
        _row("a", date(2026, 1, 1), responses=[{"id": "r1"}]),
        _row("b", date(2026, 1, 2)),
        _row("c", date(2026, 1, 3), record=[{"id": "doc-1"}]),
    ]
    _, counts = finalize_answer_rows(rows)
    assert counts == {"rows": 3, "with_response": 1, "without_response": 2, "with_record": 1}


def test_counts_are_always_computed_on_the_full_set_whatever_the_view() -> None:
    rows = [
        _row("a", date(2026, 1, 1), responses=[{"id": "r1"}]),
        _row("b", date(2026, 1, 2)),
    ]
    ordered, counts_all = finalize_answer_rows(rows)
    for view in ("all", "no-response", "with-record"):
        filtered = filter_answer_rows(ordered, view)
        # counts always come from the unfiltered set, never recomputed on `filtered`
        assert counts_all == {"rows": 2, "with_response": 1, "without_response": 1, "with_record": 0}
        assert len(filtered) <= len(ordered)


def test_filter_answer_rows_no_response() -> None:
    rows = [
        _row("a", date(2026, 1, 1), responses=[{"id": "r1"}]),
        _row("b", date(2026, 1, 2)),
    ]
    ordered, _ = finalize_answer_rows(rows)
    filtered = filter_answer_rows(ordered, "no-response")
    assert [r["charge"]["id"] for r in filtered] == ["b"]


def test_filter_answer_rows_with_record() -> None:
    rows = [
        _row("a", date(2026, 1, 1), record=[{"id": "doc-1"}]),
        _row("b", date(2026, 1, 2)),
    ]
    ordered, _ = finalize_answer_rows(rows)
    filtered = filter_answer_rows(ordered, "with-record")
    assert [r["charge"]["id"] for r in filtered] == ["a"]


def test_filter_answer_rows_all_returns_everything() -> None:
    rows = [_row("a", date(2026, 1, 1)), _row("b", date(2026, 1, 2))]
    ordered, _ = finalize_answer_rows(rows)
    assert filter_answer_rows(ordered, "all") == ordered
