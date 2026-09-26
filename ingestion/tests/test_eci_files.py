from __future__ import annotations

import json
import os
import re
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


def _real_regions() -> list:
    regions, errors = eci_files._load_regions(eci_files.DEFAULT_REGIONS_PATH)
    assert errors == []
    return regions


def _real_region_index() -> dict:
    return eci_files._region_index(_real_regions())


def _region_row(**overrides) -> dict:
    row = {"slug": "test-state", "name": "Test State", "code": "TS", "kind": "state", "aliases": []}
    row.update(overrides)
    return row


def _code_for(i: int) -> str:
    return f"{chr(65 + i // 26)}{chr(65 + i % 26)}"


def _fake_regions(count: int = 36) -> list[dict]:
    return [
        _region_row(slug=f"region-{i}", name=f"Region {i}", code=_code_for(i))
        for i in range(count)
    ]


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
        _write(tmp_path, [_entry(exclude=True, sources=[]), _entry(id="area-two")]), {}
    )
    assert errors == []
    assert [loaded.entry.id for loaded in entries] == ["area-two"]


def test_missing_area_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "file.json").write_text(json.dumps({"entries": [_entry()]}))
    _, errors = eci_files._load_entries(tmp_path, {})
    assert any("area" in e for e in errors)


# --- regions.json: reference data validated on every run, even a fixture run --------------------


def test_regions_file_validation_rejects_duplicate_code(tmp_path: Path) -> None:
    rows = _fake_regions()
    rows[1]["code"] = rows[0]["code"]
    regions_file = tmp_path / "regions.json"
    regions_file.write_text(json.dumps({"regions": rows}))
    regions, errors = eci_files._load_regions(regions_file)
    assert any("duplicate code" in e for e in errors)


def test_regions_file_validation_rejects_bad_slug(tmp_path: Path) -> None:
    rows = _fake_regions()
    rows[0]["slug"] = "not-the-right-slug"
    regions_file = tmp_path / "regions.json"
    regions_file.write_text(json.dumps({"regions": rows}))
    regions, errors = eci_files._load_regions(regions_file)
    assert any("_slugify(name)" in e for e in errors)


def test_regions_file_validation_rejects_wrong_count(tmp_path: Path) -> None:
    regions_file = tmp_path / "regions.json"
    regions_file.write_text(json.dumps({"regions": _fake_regions(5)}))
    regions, errors = eci_files._load_regions(regions_file)
    assert any("expected 36 regions" in e for e in errors)


def test_real_regions_file_is_valid() -> None:
    regions, errors = eci_files._load_regions(eci_files.DEFAULT_REGIONS_PATH)
    assert errors == []
    assert len(regions) == 36


# --- state/UT name canonicalisation: entries and states.json resolve through regions.json --------


def test_validation_rejects_unknown_state_in_entry(tmp_path: Path) -> None:
    with pytest.raises(eci_files.EciFilesValidationError) as exc:
        eci_files.run(path=_write(tmp_path, [_entry(states=["Wakanda"])]))
    assert "unknown state/UT" in str(exc.value)


def test_alias_canonicalisation_dedupes_to_the_canonical_name(tmp_path: Path) -> None:
    loaded, errors = eci_files._load_entries(
        _write(tmp_path, [_entry(states=["NCT of Delhi", "Delhi"])]), _real_region_index()
    )
    assert errors == []
    assert loaded[0].entry.states == ["Delhi"]


def test_states_file_validation_rejects_unknown_state(tmp_path: Path) -> None:
    states_file = tmp_path / "states.json"
    states_file.write_text(json.dumps({"states": [{"state": "Wakanda", "stages": []}]}))
    states, stages, errors = eci_files._load_states(states_file, _real_region_index(), {})
    assert states == []
    assert stages == []
    assert errors and "unknown state/UT" in errors[0]


def test_states_file_validation_rejects_a_region_appearing_twice(tmp_path: Path) -> None:
    states_file = tmp_path / "states.json"
    states_file.write_text(json.dumps({"states": [
        {"state": "Bihar", "stages": []},
        {"state": "Bihar", "stages": []},
    ]}))
    states, _, errors = eci_files._load_states(states_file, _real_region_index(), {})
    assert len(states) == 1
    assert any("appears twice" in e for e in errors)


def _stage(**overrides) -> dict:
    stage = {
        "stage": "before",
        "electors": 1,
        "as_of": "2025-01-01",
        "source_entry": "x",
        "url": "https://example.com",
        "tier": 1,
    }
    stage.update(overrides)
    return stage


def test_states_file_validation_rejects_duplicate_stage(tmp_path: Path) -> None:
    states_file = tmp_path / "states.json"
    states_file.write_text(json.dumps({"states": [
        {"state": "Bihar", "stages": [_stage(), _stage(stage="before", electors=2)]}
    ]}))
    _, stages, errors = eci_files._load_states(states_file, _real_region_index(), {"x": {1, 2}})
    assert len(stages) == 1
    assert any("duplicate stage" in e for e in errors)


def test_states_file_validation_rejects_a_source_entry_not_loaded(tmp_path: Path) -> None:
    states_file = tmp_path / "states.json"
    states_file.write_text(json.dumps({"states": [{"state": "Bihar", "stages": [_stage()]}]}))
    _, _, errors = eci_files._load_states(states_file, _real_region_index(), {})
    assert any("not a loaded entry id" in e for e in errors)


def test_states_file_validation_rejects_a_stage_value_missing_from_its_figures(
    tmp_path: Path,
) -> None:
    states_file = tmp_path / "states.json"
    states_file.write_text(json.dumps({"states": [
        {"state": "Bihar", "stages": [_stage(electors=999, source_entry="x")]}
    ]}))
    _, _, errors = eci_files._load_states(states_file, _real_region_index(), {"x": {1, 2, 3}})
    assert any("figures[].value" in e for e in errors)


def test_states_file_computed_stage_is_exempt_from_the_figures_check(tmp_path: Path) -> None:
    states_file = tmp_path / "states.json"
    states_file.write_text(json.dumps({"states": [
        {"state": "Bihar", "stages": [_stage(electors=999, source_entry="x", computed=True)]}
    ]}))
    _, stages, errors = eci_files._load_states(states_file, _real_region_index(), {"x": {1, 2, 3}})
    assert errors == []
    assert len(stages) == 1


def test_states_file_validation_rejects_phase_out_of_range(tmp_path: Path) -> None:
    states_file = tmp_path / "states.json"
    states_file.write_text(json.dumps({"states": [{"state": "Bihar", "phase": 7, "stages": []}]}))
    _, _, errors = eci_files._load_states(states_file, _real_region_index(), {})
    assert any("phase" in e for e in errors)


# --- national.json --------------------------------------------------------------------------


def _national_row(**overrides) -> dict:
    row = {
        "group": "phase_1",
        "measure": "before",
        "label": "Electors before the SIR",
        "scope": "Bihar",
        "electors": 1,
        "source_entry": "x",
    }
    row.update(overrides)
    return row


def test_national_file_validation_rejects_unknown_group(tmp_path: Path) -> None:
    national_file = tmp_path / "national.json"
    national_file.write_text(json.dumps({"figures": [_national_row(group="phase_9")]}))
    figures, errors = eci_files._load_national(national_file, {})
    assert figures == []
    assert errors and "group" in errors[0]


def test_national_file_validation_rejects_a_source_entry_not_loaded(tmp_path: Path) -> None:
    national_file = tmp_path / "national.json"
    national_file.write_text(json.dumps({"figures": [_national_row()]}))
    _, errors = eci_files._load_national(national_file, {})
    assert any("not a loaded entry id" in e for e in errors)


def test_national_file_validation_rejects_electors_not_in_figures(tmp_path: Path) -> None:
    national_file = tmp_path / "national.json"
    national_file.write_text(json.dumps({"figures": [_national_row(electors=999)]}))
    _, errors = eci_files._load_national(national_file, {"x": {1, 2, 3}})
    assert any("figures[].value" in e for e in errors)


def test_national_file_computed_row_must_still_match_a_figure(tmp_path: Path) -> None:
    national_file = tmp_path / "national.json"
    national_file.write_text(json.dumps({"figures": [_national_row(electors=999, computed=True)]}))
    _, errors = eci_files._load_national(national_file, {"x": {1, 2, 3}})
    assert any("figures[].value" in e for e in errors)


def test_national_file_missing_is_not_an_error() -> None:
    figures, errors = eci_files._load_national(None, {})
    assert figures == []
    assert errors == []


# --- validate_all: the real data/ files, checked with no database -------------------------------


def test_real_data_files_validate() -> None:
    payload, errors = eci_files.validate_all()
    assert errors == []
    assert payload is not None
    assert len(payload.regions) == 36
    assert len(payload.national) == 14
    assert payload.selections is not None
    assert len(payload.selections.regimes) == 3
    assert len(payload.selections.selections) == 8
    assert len(payload.selections.departures) == 6
    assert payload.media is not None
    assert len(payload.media.people) == 5


_BIRTH_RE = re.compile(r"birth|turned 65|65th birthday", re.I)


def test_real_data_files_carry_no_birth_dates() -> None:
    """Officials' profiles are public-service records only (CLAUDE.md data-handling ethic).

    Rule entries about voters' birth-date tiers (the sir-rules SIR eligibility documents) are
    exempt: they describe a legal document requirement, not an official's date of birth.
    """
    payload, errors = eci_files.validate_all()
    assert errors == []
    assert payload is not None
    checked = 0
    for area, entry in payload.entries:
        if area == "sir-rules" and entry.kind == "rule":
            continue
        assert "born" not in entry.details, f"{entry.id} still carries a details.born field"
        for field in ("summary", "notes"):
            value = getattr(entry, field)
            if value:
                assert not _BIRTH_RE.search(value), f"{entry.id}.{field} names a birth date: {value!r}"
        tenure_end = entry.details.get("tenure_end")
        if tenure_end:
            assert not _BIRTH_RE.search(tenure_end), f"{entry.id}.details.tenure_end names a birth date"
        checked += 1
    assert checked > 0


# --- person grouping: docs/eci-files/PHASE4-SPEC.md section 1.4 ---------------------------------


def _tenure(office: str, frm: str | None = None, to: str | None = None) -> dict:
    return {"office": office, "from": frm, "to": to}


def test_role_group_commission_matches_exact_office() -> None:
    assert (
        eci_files._role_group({"tenure": [_tenure("Election Commissioner", "2020-01")]})
        == "commission"
    )
    assert (
        eci_files._role_group({"tenure": [_tenure("Chief Election Commissioner", "2020-01")]})
        == "commission"
    )


def test_role_group_state_matches_chief_electoral_officer_prefix() -> None:
    assert (
        eci_files._role_group({"tenure": [_tenure("Chief Electoral Officer, Bihar", "2020-01")]})
        == "state"
    )


def test_role_group_secretariat_is_the_fallback() -> None:
    assert eci_files._role_group({"tenure": [_tenure("Secretary, ECI", "2020-01")]}) == "secretariat"
    assert eci_files._role_group({"tenure": [_tenure("Some Other Role", "2020-01")]}) == "secretariat"


def test_role_group_commission_beats_state_when_a_profile_has_both() -> None:
    details = {
        "tenure": [
            _tenure("Chief Electoral Officer, Bihar", "2018-01", "2020-01"),
            _tenure("Election Commissioner", "2020-01"),
        ]
    }
    assert eci_files._role_group(details) == "commission"


def test_is_current_true_when_a_tenure_has_from_and_no_to() -> None:
    rows = eci_files._tenure_rows({"tenure": [_tenure("Election Commissioner", "2020-01")]})
    assert eci_files._is_current(rows) is True


def test_is_current_false_when_from_is_null() -> None:
    rows = eci_files._tenure_rows({"tenure": [_tenure("Secretary, ECI")]})
    assert eci_files._is_current(rows) is False


def test_is_current_false_when_the_tenure_has_ended() -> None:
    rows = eci_files._tenure_rows(
        {"tenure": [_tenure("Election Commissioner", "2019-01", "2020-01")]}
    )
    assert eci_files._is_current(rows) is False


def test_build_person_groups_commission_order_is_chronological_by_first_from() -> None:
    names = {"a": "Alice", "b": "Bob"}
    profile_by_slug = {"a": "entry-a", "b": "entry-b"}
    details = {
        "a": {"tenure": [_tenure("Election Commissioner", "2021-01")]},
        "b": {"tenure": [_tenure("Election Commissioner", "2019-01")]},
    }
    groups = eci_files._build_person_groups(names, profile_by_slug, details)
    assert (groups["b"].role_group, groups["b"].group_rank) == ("commission", 0)
    assert (groups["a"].role_group, groups["a"].group_rank) == ("commission", 1)


def test_build_person_groups_named_people_are_ranked_alphabetically() -> None:
    names = {"z-slug": "Zed", "a-slug": "Aaron"}
    groups = eci_files._build_person_groups(names, {}, {})
    assert groups["a-slug"].role_group == "named"
    assert groups["a-slug"].group_rank == 0
    assert groups["z-slug"].role_group == "named"
    assert groups["z-slug"].group_rank == 1


# --- selections.json / people_media.json: cross-validated against the loaded entries and people --


_ENTRY_IDS = {"commissioners-kumar-cec"}
_PERSON_SLUGS = {"gyanesh-kumar"}


def _selection(**overrides) -> dict:
    base = {
        "id": "sel-1",
        "date": "2024-03-14",
        "date_precision": "day",
        "regime": "act_2023",
        "method": "selection_committee",
        "appointed": [
            {"person_slug": "gyanesh-kumar", "name": "Gyanesh Kumar", "office": "Election Commissioner"}
        ],
        "members": [],
        "search": None,
        "dissent": [],
        "entry_ids": ["commissioners-kumar-cec"],
    }
    base.update(overrides)
    return base


def _selections_file(**overrides) -> dict:
    base = {
        "regimes": [
            {
                "key": "act_2023",
                "label": "2023 Act",
                "from": None,
                "to": None,
                "rule": "A selection committee.",
                "panel": [],
                "entry_ids": ["commissioners-kumar-cec"],
            }
        ],
        "selections": [_selection()],
        "departures": [],
    }
    base.update(overrides)
    return base


def test_selections_validation_rejects_unknown_entry_id(tmp_path: Path) -> None:
    path = tmp_path / "selections.json"
    path.write_text(json.dumps(_selections_file(selections=[_selection(entry_ids=["nope"])])))
    parsed, errors = eci_files._load_selections(path, _ENTRY_IDS, _PERSON_SLUGS)
    assert parsed is None
    assert any("unknown entry id" in e for e in errors)


def test_selections_validation_rejects_unknown_person_slug(tmp_path: Path) -> None:
    path = tmp_path / "selections.json"
    bad = _selection(
        appointed=[{"person_slug": "nobody", "name": "Nobody", "office": "Election Commissioner"}]
    )
    path.write_text(json.dumps(_selections_file(selections=[bad])))
    parsed, errors = eci_files._load_selections(path, _ENTRY_IDS, _PERSON_SLUGS)
    assert parsed is None
    assert any("unknown person slug" in e for e in errors)


def test_selections_validation_rejects_unknown_regime(tmp_path: Path) -> None:
    path = tmp_path / "selections.json"
    path.write_text(json.dumps(_selections_file(selections=[_selection(regime="not-a-regime")])))
    parsed, errors = eci_files._load_selections(path, _ENTRY_IDS, _PERSON_SLUGS)
    assert parsed is None
    assert any("unknown regime" in e for e in errors)


def test_selections_validation_rejects_duplicate_selection_id(tmp_path: Path) -> None:
    path = tmp_path / "selections.json"
    path.write_text(json.dumps(_selections_file(selections=[_selection(), _selection()])))
    parsed, errors = eci_files._load_selections(path, _ENTRY_IDS, _PERSON_SLUGS)
    assert parsed is None
    assert any("duplicate selection id" in e for e in errors)


def test_selections_validation_rejects_a_member_with_empty_entry_ids(tmp_path: Path) -> None:
    path = tmp_path / "selections.json"
    bad_member = {
        "person_slug": None,
        "name": None,
        "role": "Prime Minister",
        "part": "voted_with_majority",
        "entry_ids": [],
    }
    path.write_text(json.dumps(_selections_file(selections=[_selection(members=[bad_member])])))
    parsed, errors = eci_files._load_selections(path, _ENTRY_IDS, _PERSON_SLUGS)
    assert parsed is None
    assert any("entry_ids" in e for e in errors)


def _media_person(**overrides) -> dict:
    base = {
        "slug": "gyanesh-kumar",
        "name": "Gyanesh Kumar",
        "image_url": "https://example.com/x.jpg",
        "source_page": "https://example.com/file",
        "licence": "GODL-India",
        "licence_url": "https://example.com/licence",
        "licence_review": "reviewed",
        "attribution": "Photo credit",
        "self_host": False,
    }
    base.update(overrides)
    return base


def test_media_validation_rejects_unknown_slug(tmp_path: Path) -> None:
    path = tmp_path / "people_media.json"
    path.write_text(json.dumps({"people": [_media_person(slug="nobody")]}))
    parsed, errors = eci_files._load_media(path, _PERSON_SLUGS)
    assert parsed is None
    assert any("unknown person slug" in e for e in errors)


def test_media_validation_rejects_a_bad_licence_review(tmp_path: Path) -> None:
    path = tmp_path / "people_media.json"
    path.write_text(json.dumps({"people": [_media_person(licence_review="made-up")]}))
    parsed, errors = eci_files._load_media(path, _PERSON_SLUGS)
    assert parsed is None
    assert errors


# --- Postgres integration: full replace, tier-based source codes, person linking ----------------

DATABASE_URL = os.getenv("NETA_TEST_DATABASE_URL")

pytestmark_pg = pytest.mark.skipif(
    DATABASE_URL is None, reason="NETA_TEST_DATABASE_URL is required for PostgreSQL integration tests"
)


@pytestmark_pg
def test_selections_and_media_load_when_explicitly_pointed_at_fixtures() -> None:
    from neta_core.db.engine import session_scope

    def counts() -> tuple[int, int, int, int, int]:
        with session_scope() as s:
            return (
                s.execute(text("SELECT count(*) FROM eci_file_selection_regime")).scalar_one(),
                s.execute(text("SELECT count(*) FROM eci_file_selection")).scalar_one(),
                s.execute(text("SELECT count(*) FROM eci_file_selection_person")).scalar_one(),
                s.execute(text("SELECT count(*) FROM eci_file_departure")).scalar_one(),
                s.execute(text("SELECT count(*) FROM eci_file_person_media")).scalar_one(),
            )

    eci_files.run(
        path=FIXTURES,
        selections_path=FIXTURES / "extra" / "selections.json",
        media_path=FIXTURES / "extra" / "people_media.json",
    )
    first = counts()
    assert first == (1, 1, 1, 1, 1)

    with session_scope() as s:
        url = s.execute(
            text("SELECT url FROM eci_file_person_media WHERE person_slug = 'gyanesh-kumar'")
        ).scalar_one()
    assert url == "/eci-files/people/gyanesh-kumar.jpg"

    # Idempotent: running again leaves the same rows, not doubled.
    eci_files.run(
        path=FIXTURES,
        selections_path=FIXTURES / "extra" / "selections.json",
        media_path=FIXTURES / "extra" / "people_media.json",
    )
    assert counts() == first


@pytestmark_pg
def test_selection_person_records_appointed_dissented_and_search_chair(tmp_path: Path) -> None:
    from neta_core.db.engine import session_scope

    entries_dir = tmp_path / "entries"
    entries_dir.mkdir()
    _write(
        entries_dir,
        [_entry(id="t-event", people=["Test Appointee", "Test Dissenter", "Test Chair"])],
    )
    selections_file = tmp_path / "selections.json"
    selections_file.write_text(
        json.dumps(
            {
                "regimes": [
                    {
                        "key": "act_2023",
                        "label": "2023 Act",
                        "from": None,
                        "to": None,
                        "rule": "A selection committee.",
                        "panel": [],
                        "entry_ids": ["t-event"],
                    }
                ],
                "selections": [
                    {
                        "id": "sel-test",
                        "date": "2024-03-14",
                        "date_precision": "day",
                        "regime": "act_2023",
                        "method": "selection_committee",
                        "appointed": [
                            {
                                "person_slug": "test-appointee",
                                "name": "Test Appointee",
                                "office": "Election Commissioner",
                                "took_charge": "2024-03-15",
                            }
                        ],
                        "members": [
                            {
                                "person_slug": "test-dissenter",
                                "name": "Test Dissenter",
                                "role": "Leader of Opposition",
                                "part": "dissented",
                                "entry_ids": ["t-event"],
                            }
                        ],
                        "search": {
                            "by": "Search committee",
                            "chair_slug": "test-chair",
                            "shortlist_size": None,
                            "shortlist": None,
                            "shortlist_source": None,
                            "entry_ids": ["t-event"],
                        },
                        "dissent": [],
                        "entry_ids": ["t-event"],
                    }
                ],
                "departures": [],
            }
        )
    )

    eci_files.run(path=entries_dir, selections_path=selections_file)
    with session_scope() as s:
        parts = dict(
            s.execute(
                text("SELECT person_slug, part FROM eci_file_selection_person ORDER BY person_slug")
            ).all()
        )
    assert parts == {
        "test-appointee": "appointed",
        "test-chair": "search_chair",
        "test-dissenter": "dissented",
    }


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
    ]), {})
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
    _, stages, errors = eci_files._load_states(states_file, _real_region_index(), {"x": {1}})
    assert stages == []
    assert errors and "stage" in errors[0]


def test_states_file_missing_is_not_an_error() -> None:
    states, stages, errors = eci_files._load_states(Path("/nonexistent/states.json"), {}, {})
    assert states == []
    assert stages == []
    assert errors == []


def test_states_file_none_is_not_an_error() -> None:
    states, stages, errors = eci_files._load_states(None, {}, {})
    assert states == []
    assert stages == []
    assert errors == []


@pytestmark_pg
def test_running_with_an_explicit_entries_path_does_not_touch_states_or_headline() -> None:
    """A fixture-pointed run must never depend on (or clear against) the real repo data files."""
    from neta_core.db.engine import session_scope

    eci_files.run(path=FIXTURES)
    with session_scope() as s:
        assert s.execute(text("SELECT count(*) FROM eci_file_region")).scalar_one() == 36
        assert s.execute(text("SELECT count(*) FROM eci_file_state_stage")).scalar_one() == 0
        assert s.execute(text("SELECT count(*) FROM eci_file_national_figure")).scalar_one() == 0
        assert s.execute(text("SELECT count(*) FROM eci_file_headline")).scalar_one() == 0
        assert s.execute(text("SELECT count(*) FROM eci_file_key_moment")).scalar_one() == 0


@pytestmark_pg
def test_states_and_headline_load_when_explicitly_pointed_at_fixtures() -> None:
    from neta_core.db.engine import session_scope

    eci_files.run(
        path=FIXTURES,
        states_path=FIXTURES / "extra" / "states.json",
        headline_path=FIXTURES / "extra" / "headline.json",
        national_path=FIXTURES / "extra" / "national.json",
    )
    with session_scope() as s:
        assert s.execute(text("SELECT count(*) FROM eci_file_region")).scalar_one() == 36

        stage = s.execute(
            text("SELECT region_slug, stage, electors, computed, source_entry_id, tier "
                 "FROM eci_file_state_stage WHERE stage = 'draft'")
        ).one()
        assert (stage.region_slug, stage.electors, stage.computed) == ("bihar", 72400000, False)
        assert stage.source_entry_id == "sir-rules-2025-notification"

        national = s.execute(
            text("SELECT grp, measure, electors FROM eci_file_national_figure")
        ).one()
        assert (national.grp, national.measure, national.electors) == ("phase_1", "draft", 72400000)

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
        national_path=FIXTURES / "extra" / "national.json",
    )
    with session_scope() as s:
        assert s.execute(text("SELECT count(*) FROM eci_file_region")).scalar_one() == 36
        assert s.execute(text("SELECT count(*) FROM eci_file_state_stage")).scalar_one() == 2
        assert s.execute(text("SELECT count(*) FROM eci_file_national_figure")).scalar_one() == 1
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


# --- phase 5: objections.json / pairs.json / rule_diffs.json / case_orders.json / merges.json ----

_P5_ENTRY_IDS = {
    "p5-claim", "p5-response", "p5-documented", "p5-rule", "p5-case", "p5-case-2", "p5-order",
}
_P5_ENTRY_STATUS = {
    "p5-claim": "claim",
    "p5-response": "response",
    "p5-documented": "documented",
    "p5-rule": "documented",
    "p5-case": "documented",
    "p5-case-2": "documented",
    "p5-order": "documented",
}
_P5_ENTRY_KIND = {
    "p5-claim": "statement",
    "p5-response": "statement",
    "p5-documented": "event",
    "p5-rule": "rule",
    "p5-case": "case",
    "p5-case-2": "case",
    "p5-order": "event",
}
_P5_PERSON_SLUGS = {"test-commissioner"}


def _objection(**overrides) -> dict:
    base = {
        "n": 1,
        "date": "2026-01-01",
        "date_precision": "day",
        "by": ["Test Commissioner"],
        "concerns": "A concern.",
        "entry_ids": ["p5-documented"],
        "followed_by": None,
        "public": False,
    }
    base.update(overrides)
    return base


def _objections_file(**overrides) -> dict:
    base = {
        "objections": [_objection()],
        "missing": 0,
        "notes": None,
        "report_entry_id": "p5-documented",
        "response_entry_id": "p5-response",
    }
    base.update(overrides)
    return base


def test_objections_validation_rejects_unknown_entry_id(tmp_path: Path) -> None:
    path = tmp_path / "objections.json"
    path.write_text(json.dumps(_objections_file(objections=[_objection(entry_ids=["nope"])])))
    parsed, errors = eci_files._load_objections(path, _P5_ENTRY_IDS, _P5_PERSON_SLUGS)
    assert parsed is None
    assert any("unknown entry id" in e for e in errors)


def test_objections_validation_rejects_n_gap(tmp_path: Path) -> None:
    path = tmp_path / "objections.json"
    path.write_text(json.dumps(_objections_file(objections=[_objection(n=1), _objection(n=3)])))
    parsed, errors = eci_files._load_objections(path, _P5_ENTRY_IDS, _P5_PERSON_SLUGS)
    assert parsed is None
    assert any("not contiguous" in e for e in errors)


def test_objections_validation_rejects_followed_by_token_for_a_missing_entry(tmp_path: Path) -> None:
    path = tmp_path / "objections.json"
    path.write_text(
        json.dumps(_objections_file(objections=[_objection(followed_by="See (sir-rules-nope).")]))
    )
    parsed, errors = eci_files._load_objections(path, _P5_ENTRY_IDS, _P5_PERSON_SLUGS)
    assert parsed is None
    assert any("followed_by" in e and "unknown entry id" in e for e in errors)


def test_objections_validation_rejects_unknown_person(tmp_path: Path) -> None:
    path = tmp_path / "objections.json"
    path.write_text(json.dumps(_objections_file(objections=[_objection(by=["Nobody At All"])])))
    parsed, errors = eci_files._load_objections(path, _P5_ENTRY_IDS, _P5_PERSON_SLUGS)
    assert parsed is None
    assert any("unknown person" in e for e in errors)


def _pair(**overrides) -> dict:
    base = {
        "charge_id": "p5-claim",
        "also_recorded_as": [],
        "response_ids": ["p5-response"],
        "record_ids": ["p5-documented"],
        "related": [],
        "note": None,
    }
    base.update(overrides)
    return base


def _pairs_file(**overrides) -> dict:
    base = {"about": "t", "built_on": "2026-01-01", "pairs": [_pair()], "unpaired_responses": []}
    base.update(overrides)
    return base


def test_pairs_validation_rejects_unknown_entry_id(tmp_path: Path) -> None:
    path = tmp_path / "pairs.json"
    path.write_text(json.dumps(_pairs_file(pairs=[_pair(charge_id="nope")])))
    parsed, errors = eci_files._load_pairs(path, _P5_ENTRY_IDS, _P5_ENTRY_STATUS)
    assert parsed is None
    assert any("unknown entry id" in e for e in errors)


def test_pairs_validation_rejects_a_record_id_that_isnt_documented(tmp_path: Path) -> None:
    path = tmp_path / "pairs.json"
    path.write_text(json.dumps(_pairs_file(pairs=[_pair(record_ids=["p5-claim"])])))
    parsed, errors = eci_files._load_pairs(path, _P5_ENTRY_IDS, _P5_ENTRY_STATUS)
    assert parsed is None
    assert any("is not a documented entry" in e for e in errors)


def test_pairs_validation_rejects_a_response_id_that_isnt_a_response(tmp_path: Path) -> None:
    path = tmp_path / "pairs.json"
    path.write_text(json.dumps(_pairs_file(pairs=[_pair(response_ids=["p5-documented"])])))
    parsed, errors = eci_files._load_pairs(path, _P5_ENTRY_IDS, _P5_ENTRY_STATUS)
    assert parsed is None
    assert any("is not a response entry" in e for e in errors)


def test_pairs_validation_rejects_an_id_that_is_both_a_charge_and_also_recorded_as(
    tmp_path: Path,
) -> None:
    path = tmp_path / "pairs.json"
    path.write_text(
        json.dumps(
            _pairs_file(
                pairs=[
                    _pair(charge_id="p5-claim", also_recorded_as=[]),
                    _pair(charge_id="p5-documented", also_recorded_as=["p5-claim"]),
                ]
            )
        )
    )
    parsed, errors = eci_files._load_pairs(path, _P5_ENTRY_IDS, _P5_ENTRY_STATUS)
    assert parsed is None
    assert any("both a charge_id and an also_recorded_as" in e for e in errors)


def _rule_diff(**overrides) -> dict:
    base = {
        "id": "p5-diff",
        "rule_entry_id": "p5-rule",
        "title": "Test rule diff",
        "document": "Test Rules, 2026",
        "before_label": "Before",
        "after_label": "After",
        "before": ["a"],
        "after": ["a", "b"],
        "before_status": "verbatim",
        "after_status": "verbatim",
        "text_status": "verbatim",
        "excerpt": False,
        "quoted_lines_before": [],
        "quoted_lines_after": [],
        "source_urls": ["https://example.com/doc"],
        "note": None,
        "related_entry_ids": [],
    }
    base.update(overrides)
    return base


def _rule_diffs_file(**overrides) -> dict:
    base = {
        "about": "t",
        "built_on": "2026-01-01",
        "text_statuses": ["verbatim", "quoted in reporting", "paraphrased from reporting"],
        "diffs": [_rule_diff()],
        "gaps": [],
    }
    base.update(overrides)
    return base


def test_rule_diffs_validation_rejects_unknown_rule_entry_id(tmp_path: Path) -> None:
    path = tmp_path / "rule_diffs.json"
    path.write_text(json.dumps(_rule_diffs_file(diffs=[_rule_diff(rule_entry_id="nope")])))
    parsed, errors = eci_files._load_rule_diffs(path, _P5_ENTRY_IDS, _P5_ENTRY_KIND)
    assert parsed is None
    assert any("unknown rule_entry_id" in e for e in errors)


def test_rule_diffs_validation_rejects_a_rule_entry_id_not_kind_rule(tmp_path: Path) -> None:
    path = tmp_path / "rule_diffs.json"
    path.write_text(json.dumps(_rule_diffs_file(diffs=[_rule_diff(rule_entry_id="p5-documented")])))
    parsed, errors = eci_files._load_rule_diffs(path, _P5_ENTRY_IDS, _P5_ENTRY_KIND)
    assert parsed is None
    assert any("is not kind=rule" in e for e in errors)


def test_rule_diffs_validation_rejects_a_text_status_that_doesnt_match_its_sides(
    tmp_path: Path,
) -> None:
    path = tmp_path / "rule_diffs.json"
    bad = _rule_diff(
        before_status="paraphrased from reporting", after_status="verbatim", text_status="verbatim"
    )
    path.write_text(json.dumps(_rule_diffs_file(diffs=[bad])))
    parsed, errors = eci_files._load_rule_diffs(path, _P5_ENTRY_IDS, _P5_ENTRY_KIND)
    assert parsed is None
    assert any("is not the weaker of" in e for e in errors)


def _case_item(**overrides) -> dict:
    base = {"entry_id": "p5-order", "role": "order", "note": None}
    base.update(overrides)
    return base


def _case(**overrides) -> dict:
    base = {
        "slug": "p5-case-slug",
        "short_name": "P5 Case",
        "case_entry_id": "p5-case",
        "court": "Test Court",
        "short_status": "pending",
        "status_note": None,
        "parties": {"petitioners": [], "respondents": []},
        "items": [_case_item()],
    }
    base.update(overrides)
    return base


def _cases_file(**overrides) -> dict:
    base = {
        "about": "t",
        "built_on": "2026-01-01",
        "roles": ["order", "judgment", "hearing", "filing", "listing", "recusal", "compliance", "related"],
        "cases": [_case()],
        "unmapped": [],
    }
    base.update(overrides)
    return base


def test_cases_validation_rejects_unknown_case_entry_id(tmp_path: Path) -> None:
    path = tmp_path / "case_orders.json"
    path.write_text(json.dumps(_cases_file(cases=[_case(case_entry_id="nope")])))
    parsed, errors = eci_files._load_cases(path, _P5_ENTRY_IDS, _P5_ENTRY_KIND)
    assert parsed is None
    assert any("unknown case_entry_id" in e for e in errors)


def test_cases_validation_rejects_a_duplicate_case_item(tmp_path: Path) -> None:
    path = tmp_path / "case_orders.json"
    path.write_text(
        json.dumps(
            _cases_file(
                cases=[
                    _case(slug="case-a", case_entry_id="p5-case"),
                    _case(slug="case-b", case_entry_id="p5-case-2"),
                ]
            )
        )
    )
    parsed, errors = eci_files._load_cases(path, _P5_ENTRY_IDS, _P5_ENTRY_KIND)
    assert parsed is None
    assert any("is an item of two cases" in e for e in errors)


def test_cases_validation_rejects_a_case_entry_as_its_own_item(tmp_path: Path) -> None:
    path = tmp_path / "case_orders.json"
    path.write_text(json.dumps(_cases_file(cases=[_case(items=[_case_item(entry_id="p5-case")])])))
    parsed, errors = eci_files._load_cases(path, _P5_ENTRY_IDS, _P5_ENTRY_KIND)
    assert parsed is None
    assert any("case entry is its own item" in e for e in errors)


def test_load_merges_builds_the_drop_to_keep_map(tmp_path: Path) -> None:
    path = tmp_path / "merges.json"
    path.write_text(
        json.dumps({"merges": [{"keep": "kept-id", "drop": ["dropped-a", "dropped-b"]}]})
    )
    mapping, errors = eci_files._load_merges(path)
    assert errors == []
    assert mapping == {"dropped-a": "kept-id", "dropped-b": "kept-id"}


def test_response_to_pointing_at_a_dropped_id_is_rewritten_to_the_kept_id() -> None:
    loaded = [
        eci_files.LoadedEntry(
            area="area",
            entry=eci_files.Entry.model_validate(_entry(id="e1", response_to="dropped-id")),
        )
    ]
    resolved = eci_files._resolve_response_links(loaded, {"dropped-id": "kept-id"})
    assert resolved == 1
    assert loaded[0].entry.response_to == "kept-id"


def test_real_data_files_phase5_matches_spec() -> None:
    payload, errors = eci_files.validate_all()
    assert errors == []
    assert payload is not None
    assert payload.resolved_response_count == 5

    assert payload.objections is not None
    assert len(payload.objections.objections) == 11
    assert payload.objections.missing == 3

    assert payload.pairs is not None
    assert len(payload.pairs.pairs) == 61
    assert sum(1 for p in payload.pairs.pairs if not p.response_ids) == 27
    assert sum(1 for p in payload.pairs.pairs if p.record_ids) == 14
    assert len(payload.pairs.unpaired_responses) == 1

    assert payload.rule_diffs is not None
    assert len(payload.rule_diffs.diffs) == 7

    assert payload.cases is not None
    assert len(payload.cases.cases) == 5
    assert sum(len(c.items) for c in payload.cases.cases) == 51


# --- Postgres integration: phase 5 full replace across all eleven tables -------------------------


@pytestmark_pg
def test_phase5_fixture_loads_all_eleven_tables_idempotently() -> None:
    from neta_core.db.engine import session_scope

    tables = (
        "eci_file_objection",
        "eci_file_objection_person",
        "eci_file_objection_entry",
        "eci_file_objection_meta",
        "eci_file_pair",
        "eci_file_pair_item",
        "eci_file_unpaired_response",
        "eci_file_rule_diff",
        "eci_file_rule_diff_entry",
        "eci_file_case",
        "eci_file_case_item",
    )

    def counts() -> tuple[int, ...]:
        with session_scope() as s:
            return tuple(
                s.execute(text(f"SELECT count(*) FROM {t}")).scalar_one()  # noqa: S608
                for t in tables
            )

    kwargs = dict(
        path=FIXTURES / "extra" / "phase5_entries",
        objections_path=FIXTURES / "extra" / "objections.json",
        pairs_path=FIXTURES / "extra" / "pairs.json",
        rule_diffs_path=FIXTURES / "extra" / "rule_diffs.json",
        cases_path=FIXTURES / "extra" / "case_orders.json",
    )

    eci_files.run(**kwargs)
    first = counts()
    assert first == (1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1)

    eci_files.run(**kwargs)
    assert counts() == first


@pytestmark_pg
def test_deleting_an_entry_removes_its_pair_case_and_diff_rows(tmp_path: Path) -> None:
    from neta_core.db.engine import session_scope

    entries_dir = tmp_path / "entries"
    entries_dir.mkdir()

    def write_entries(*, include_shared: bool) -> None:
        entries = [
            _entry(id="b-rule-1", kind="rule"),
            _entry(id="b-case-1", kind="case"),
            _entry(id="b-charge-1", kind="statement", status="claim"),
        ]
        if include_shared:
            entries.append(_entry(id="b-shared-1", kind="event"))
        _write(entries_dir, entries)

    def write_phase5(*, include_shared: bool) -> None:
        related = [{"id": "b-shared-1", "why": "testing"}] if include_shared else []
        (tmp_path / "pairs.json").write_text(
            json.dumps(
                {
                    "about": "t",
                    "built_on": "2026-01-01",
                    "pairs": [
                        {
                            "charge_id": "b-charge-1",
                            "also_recorded_as": [],
                            "response_ids": [],
                            "record_ids": [],
                            "related": related,
                            "note": None,
                        }
                    ],
                    "unpaired_responses": [],
                }
            )
        )
        related_entry_ids = ["b-shared-1"] if include_shared else []
        (tmp_path / "rule_diffs.json").write_text(
            json.dumps(
                {
                    "about": "t",
                    "built_on": "2026-01-01",
                    "text_statuses": [
                        "verbatim", "quoted in reporting", "paraphrased from reporting"
                    ],
                    "diffs": [
                        {
                            "id": "b-diff-1",
                            "rule_entry_id": "b-rule-1",
                            "title": "t",
                            "document": "d",
                            "before_label": "Before",
                            "after_label": "After",
                            "before": ["a"],
                            "after": ["a"],
                            "before_status": "verbatim",
                            "after_status": "verbatim",
                            "text_status": "verbatim",
                            "excerpt": False,
                            "quoted_lines_before": [],
                            "quoted_lines_after": [],
                            "source_urls": ["https://example.com/b"],
                            "note": None,
                            "related_entry_ids": related_entry_ids,
                        }
                    ],
                    "gaps": [],
                }
            )
        )
        items = [{"entry_id": "b-shared-1", "role": "order", "note": None}] if include_shared else []
        (tmp_path / "case_orders.json").write_text(
            json.dumps(
                {
                    "about": "t",
                    "built_on": "2026-01-01",
                    "roles": [
                        "order", "judgment", "hearing", "filing", "listing", "recusal",
                        "compliance", "related",
                    ],
                    "cases": [
                        {
                            "slug": "b-case",
                            "short_name": "B Case",
                            "case_entry_id": "b-case-1",
                            "court": "Test Court",
                            "short_status": "pending",
                            "status_note": None,
                            "parties": {"petitioners": [], "respondents": []},
                            "items": items,
                        }
                    ],
                    "unmapped": [],
                }
            )
        )

    def counts() -> tuple[int, int, int]:
        with session_scope() as s:
            return (
                s.execute(
                    text("SELECT count(*) FROM eci_file_pair_item WHERE role = 'related'")
                ).scalar_one(),
                s.execute(text("SELECT count(*) FROM eci_file_case_item")).scalar_one(),
                s.execute(text("SELECT count(*) FROM eci_file_rule_diff_entry")).scalar_one(),
            )

    kwargs = dict(
        path=entries_dir,
        pairs_path=tmp_path / "pairs.json",
        rule_diffs_path=tmp_path / "rule_diffs.json",
        cases_path=tmp_path / "case_orders.json",
    )

    write_entries(include_shared=True)
    write_phase5(include_shared=True)
    eci_files.run(**kwargs)
    assert counts() == (1, 1, 1)

    write_entries(include_shared=False)
    write_phase5(include_shared=False)
    eci_files.run(**kwargs)
    assert counts() == (0, 0, 0)

    with session_scope() as s:
        assert s.execute(text("SELECT count(*) FROM eci_file_pair")).scalar_one() == 1
        assert s.execute(text("SELECT count(*) FROM eci_file_case")).scalar_one() == 1
        assert s.execute(text("SELECT count(*) FROM eci_file_rule_diff")).scalar_one() == 1
