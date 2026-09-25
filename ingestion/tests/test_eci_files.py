from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from sqlalchemy import text

from neta_ingest.pipelines.curated import eci_files

FIXTURES = Path(__file__).parent / "fixtures" / "eci_files"

_BASE_ENTRY = {
    "id": "area-one",
    "kind": "event",
    "date": "2025-01-01",
    "date_precision": "day",
    "title": "Something happened",
    "summary": "A neutral summary of what happened.",
    "status": "documented",
    "sources": [
        {
            "url": "https://eci.gov.in/doc-1",
            "publisher": "Election Commission of India",
            "tier": 1,
        }
    ],
    "check": "checked",
}


def _write(tmp_path: Path, entries: list[dict], *, area: str = "area") -> Path:
    (tmp_path / "file.json").write_text(json.dumps({"area": area, "entries": entries}))
    return tmp_path


def _entry(**overrides) -> dict:
    entry = dict(_BASE_ENTRY)
    entry.update(overrides)
    return entry


# --- validation: each bad case is rejected, and every error is collected at once ----------------


def test_validation_rejects_missing_source(tmp_path: Path) -> None:
    with pytest.raises(eci_files.EciFilesValidationError) as exc:
        eci_files.run(path=_write(tmp_path, [_entry(sources=[])]))
    assert "sources" in str(exc.value)


def test_validation_rejects_unknown_status(tmp_path: Path) -> None:
    with pytest.raises(eci_files.EciFilesValidationError) as exc:
        eci_files.run(path=_write(tmp_path, [_entry(status="rigged")]))
    assert "status" in str(exc.value)


def test_validation_rejects_bad_date(tmp_path: Path) -> None:
    with pytest.raises(eci_files.EciFilesValidationError) as exc:
        eci_files.run(path=_write(tmp_path, [_entry(date="not-a-date")]))
    assert "date" in str(exc.value)


def test_validation_rejects_duplicate_id(tmp_path: Path) -> None:
    with pytest.raises(eci_files.EciFilesValidationError) as exc:
        eci_files.run(path=_write(tmp_path, [_entry(), _entry()]))
    assert "duplicate" in str(exc.value)


def test_validation_rejects_quote_over_15_words(tmp_path: Path) -> None:
    long_quote = " ".join(["word"] * 16)
    with pytest.raises(eci_files.EciFilesValidationError) as exc:
        eci_files.run(
            path=_write(
                tmp_path,
                [_entry(sources=[{**_BASE_ENTRY["sources"][0], "quote": long_quote}])],
            )
        )
    assert "quote" in str(exc.value)


def test_validation_collects_every_error_at_once(tmp_path: Path) -> None:
    with pytest.raises(eci_files.EciFilesValidationError) as exc:
        eci_files.run(
            path=_write(
                tmp_path,
                [_entry(id="a", status="rigged"), _entry(id="b", sources=[])],
            )
        )
    assert len(exc.value.errors) == 2


def test_excluded_entries_are_skipped_without_validation(tmp_path: Path) -> None:
    # An excluded, incomplete draft (no sources) must not block a load or raise.
    entries, errors = eci_files._load_entries(
        _write(tmp_path, [_entry(exclude=True, sources=[]), _entry(id="area-two")])
    )
    assert errors == []
    assert [loaded.entry.id for loaded in entries] == ["area-two"]


def test_missing_area_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "file.json").write_text(json.dumps({"entries": [_entry()]}))
    _, errors = eci_files._load_entries(tmp_path)
    assert any("area" in e for e in errors)


# --- Postgres integration: full replace, tier-based source codes, person linking ----------------

DATABASE_URL = os.getenv("NETA_TEST_DATABASE_URL")

pytestmark_pg = pytest.mark.skipif(
    DATABASE_URL is None, reason="NETA_TEST_DATABASE_URL is required for PostgreSQL integration tests"
)


@pytestmark_pg
def test_loading_the_fixture_twice_leaves_the_same_row_counts() -> None:
    from neta_core.db.engine import session_scope

    def counts() -> tuple[int, int, int, int]:
        with session_scope() as s:
            return (
                s.execute(text("SELECT count(*) FROM eci_file_entry")).scalar_one(),
                s.execute(text("SELECT count(*) FROM eci_file_person")).scalar_one(),
                s.execute(text("SELECT count(*) FROM eci_file_entry_person")).scalar_one(),
                s.execute(text("SELECT count(*) FROM eci_file_citation")).scalar_one(),
            )

    eci_files.run(path=FIXTURES)
    first = counts()
    assert first == (6, 1, 2, 7)

    eci_files.run(path=FIXTURES)
    assert counts() == first


@pytestmark_pg
def test_citations_get_the_source_code_matching_their_tier() -> None:
    from neta_core.db.engine import session_scope

    eci_files.run(path=FIXTURES)
    with session_scope() as s:
        rows = s.execute(
            text("""
                SELECT c.tier, src.code
                FROM eci_file_citation c
                JOIN source_ref sr ON sr.id = c.source_ref_id
                JOIN source src ON src.id = sr.source_id
            """)
        ).all()
    assert rows
    for tier, code in rows:
        assert code == eci_files._TIER_TO_SOURCE_CODE[tier]


@pytestmark_pg
def test_person_linking_matches_profile_and_mentions() -> None:
    from neta_core.db.engine import session_scope

    eci_files.run(path=FIXTURES)
    with session_scope() as s:
        person = s.execute(
            text("SELECT slug, name, profile_entry_id FROM eci_file_person WHERE slug = 'gyanesh-kumar'")
        ).one()
        mentions = s.execute(
            text("SELECT entry_id FROM eci_file_entry_person WHERE person_slug = 'gyanesh-kumar' ORDER BY entry_id")
        ).scalars().all()

    assert person.name == "Gyanesh Kumar"
    assert person.profile_entry_id == "commissioners-kumar-cec"
    assert mentions == ["commissioners-kumar-appointment", "commissioners-kumar-cec"]


def test_month_and_year_dates_load_as_the_first_day_of_the_period(tmp_path: Path) -> None:
    loaded, errors = eci_files._load_entries(_write(tmp_path, [
        _entry(id="a-month", date="2026-07", date_precision="month"),
        _entry(id="a-year", date="2019", date_precision="year"),
    ]))
    assert errors == []
    dates = {e.id: e.date.isoformat() for _, e in loaded}
    assert dates == {"a-month": "2026-07-01", "a-year": "2019-01-01"}


def _person(entry_id: str, name: str, *, check: str = "checked") -> dict:
    return _entry(id=entry_id, kind="person", title=f"{name}: Election Commissioner", people=[name], check=check)


@pytestmark_pg
def test_spellings_that_slug_alike_are_one_person(tmp_path: Path) -> None:
    from neta_core.db.engine import session_scope

    eci_files.run(path=_write(tmp_path, [
        _entry(id="a-one", people=["P. Pawan"]),
        _entry(id="a-two", people=["P Pawan", "P. Pawan"]),
    ]))
    with session_scope() as s:
        people = s.execute(text("SELECT slug FROM eci_file_person")).scalars().all()
        links = s.execute(text("SELECT count(*) FROM eci_file_entry_person")).scalar_one()
    assert people == ["p-pawan"]
    assert links == 2


@pytestmark_pg
def test_a_checked_profile_from_a_people_area_wins(tmp_path: Path) -> None:
    from neta_core.db.engine import session_scope

    (tmp_path / "a.json").write_text(json.dumps({"area": "commissioners", "entries": [_person("c-goel", "Arun Goel")]}))
    (tmp_path / "z.json").write_text(json.dumps(
        {"area": "selection-law", "entries": [_person("s-goel", "Arun Goel", check="unchecked")]}))
    eci_files.run(path=tmp_path)
    with session_scope() as s:
        profile = s.execute(
            text("SELECT profile_entry_id FROM eci_file_person WHERE slug = 'arun-goel'")).scalar_one()
    assert profile == "c-goel"


# --- lanes: the first matching rule wins (redesign spec 1a) --------------------------------------


def _lane_of(**overrides) -> str:
    return eci_files._derive_lane(eci_files.Entry.model_validate(_entry(**overrides)))


def test_lane_response_status_goes_to_responses() -> None:
    assert _lane_of(status="response") == "responses"


def test_lane_claim_status_goes_to_claims() -> None:
    assert _lane_of(status="claim") == "claims"


def test_lane_courts_topic_goes_to_courts() -> None:
    assert _lane_of(status="documented", topics=["courts"]) == "courts"


def test_lane_case_kind_goes_to_courts() -> None:
    assert _lane_of(status="documented", kind="case") == "courts"


def test_lane_dissent_topic_goes_to_inside() -> None:
    assert _lane_of(status="documented", topics=["dissent"]) == "inside"


def test_lane_everything_else_goes_to_commission() -> None:
    assert _lane_of(status="documented", kind="event", topics=[]) == "commission"


def test_lane_precedence_a_response_tagged_courts_goes_to_responses() -> None:
    assert _lane_of(status="response", topics=["courts"], kind="case") == "responses"


def test_lane_precedence_a_claim_tagged_dissent_goes_to_claims() -> None:
    assert _lane_of(status="claim", topics=["dissent"]) == "claims"


def test_lane_precedence_courts_beats_dissent() -> None:
    assert _lane_of(status="documented", topics=["courts", "dissent"]) == "courts"


@pytestmark_pg
def test_lane_is_persisted_on_load() -> None:
    from neta_core.db.engine import session_scope

    eci_files.run(path=FIXTURES)
    with session_scope() as s:
        lane = s.execute(
            text("SELECT lane FROM eci_file_entry WHERE id = 'commissioners-opposition-claim'")
        ).scalar_one()
    assert lane == "claims"


# --- state figures: states.json is optional, validated, and loaded as a full replace -------------


def test_state_stage_validation_rejects_unknown_stage(tmp_path: Path) -> None:
    states_file = tmp_path / "states.json"
    states_file.write_text(json.dumps({"states": [{"state": "Bihar", "stages": [{
        "stage": "not-a-stage", "electors": 1, "as_of": "2025-01-01",
        "source_entry": "x", "url": "https://example.com", "tier": 1,
    }]}]}))
    stages, errors = eci_files._load_state_stages(states_file)
    assert stages == []
    assert errors and "stage" in errors[0]


def test_states_file_missing_is_not_an_error() -> None:
    stages, errors = eci_files._load_state_stages(Path("/nonexistent/states.json"))
    assert stages == []
    assert errors == []


def test_states_file_none_is_not_an_error() -> None:
    stages, errors = eci_files._load_state_stages(None)
    assert stages == []
    assert errors == []


@pytestmark_pg
def test_running_with_an_explicit_entries_path_does_not_touch_states_or_headline() -> None:
    """A fixture-pointed run must never depend on (or clear against) the real repo data files."""
    from neta_core.db.engine import session_scope

    eci_files.run(path=FIXTURES)
    with session_scope() as s:
        assert s.execute(text("SELECT count(*) FROM eci_file_state_stage")).scalar_one() == 0
        assert s.execute(text("SELECT count(*) FROM eci_file_headline")).scalar_one() == 0
        assert s.execute(text("SELECT count(*) FROM eci_file_key_moment")).scalar_one() == 0


@pytestmark_pg
def test_states_and_headline_load_when_explicitly_pointed_at_fixtures() -> None:
    from neta_core.db.engine import session_scope

    eci_files.run(
        path=FIXTURES,
        states_path=FIXTURES / "extra" / "states.json",
        headline_path=FIXTURES / "extra" / "headline.json",
    )
    with session_scope() as s:
        stage = s.execute(
            text("SELECT state, stage, electors, computed, source_entry_id, tier "
                 "FROM eci_file_state_stage WHERE stage = 'draft'")
        ).one()
        assert (stage.state, stage.electors, stage.computed) == ("Bihar", 72400000, False)
        assert stage.source_entry_id == "sir-rules-2025-notification"

        headline_rows = s.execute(
            text("SELECT position, value, entry_id FROM eci_file_headline ORDER BY position")
        ).all()
        assert [r.position for r in headline_rows] == [1, 2]
        assert headline_rows[0].entry_id == "commissioners-kumar-appointment"

        key_moments = s.execute(
            text("SELECT entry_id FROM eci_file_key_moment ORDER BY position")
        ).scalars().all()
        assert key_moments == ["commissioners-kumar-cec", "sir-rules-2025-notification"]

    # Idempotent: running again leaves the same rows, not doubled.
    eci_files.run(
        path=FIXTURES,
        states_path=FIXTURES / "extra" / "states.json",
        headline_path=FIXTURES / "extra" / "headline.json",
    )
    with session_scope() as s:
        assert s.execute(text("SELECT count(*) FROM eci_file_state_stage")).scalar_one() == 2
        assert s.execute(text("SELECT count(*) FROM eci_file_headline")).scalar_one() == 2


def test_headline_validation_rejects_missing_field(tmp_path: Path) -> None:
    headline_file = tmp_path / "headline.json"
    headline_file.write_text(json.dumps({"headline": [{"value": "1"}], "key_moments": []}))
    headline, errors = eci_files._load_headline(headline_file)
    assert headline is None
    assert errors and "label" in errors[0]


def test_headline_file_missing_is_not_an_error() -> None:
    headline, errors = eci_files._load_headline(Path("/nonexistent/headline.json"))
    assert headline is None
    assert errors == []
