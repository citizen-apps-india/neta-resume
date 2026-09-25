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
