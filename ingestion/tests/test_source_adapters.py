"""Representative API, crawl, and feed adapters emit replayable raw envelopes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import httpx
import pytest

from neta_core.pipeline import (
    ExtractionContext,
    FileRawObjectStore,
    HttpSourceAdapter,
    capture_raw,
)
from neta_ingest.extraction import pipeline_execution_scope, source_extraction_context
from neta_sources.google_news import client as google_news
from neta_sources.myneta import client as myneta
from neta_sources.prs import client as prs
from neta_sources.sansad import client as sansad
from neta_sources.sansad import committees as sansad_committees
from neta_sources.worldbank import client as worldbank

FIXTURES = Path(__file__).parent / "fixtures"


def _http_adapter(
    payload: bytes,
    content_type: str,
    *,
    extra_headers: dict[str, str] | None = None,
    status_code: int = 200,
) -> tuple[HttpSourceAdapter, list[tuple[str, dict[str, object]]]]:
    calls: list[tuple[str, dict[str, object]]] = []

    def get(url: str, **kwargs: object) -> httpx.Response:
        calls.append((url, kwargs))
        headers = {"content-type": content_type, **(extra_headers or {})}
        return httpx.Response(
            status_code,
            content=payload,
            headers=headers,
            request=httpx.Request("GET", url),
        )

    return HttpSourceAdapter(get=get), calls


def _context(source_id: str, tmp_path: Path, run_id: str = "test-run"):
    return source_extraction_context(
        source_id,
        pipeline_run_id=run_id,
        object_store=FileRawObjectStore(tmp_path),
    )


def test_world_bank_api_adapter_is_content_addressed_and_preserves_missing(
    tmp_path: Path,
) -> None:
    payload = json.dumps(
        [
            {"page": 1, "pages": 1},
            [
                {"indicator": {"value": "Example series"}, "date": "2024", "value": 7.5},
                {"indicator": {"value": "Example series"}, "date": "2023", "value": None},
                {"indicator": {"value": "Example series"}, "date": "2022", "value": 4.0},
            ],
        ]
    ).encode()
    adapter, calls = _http_adapter(
        payload,
        "application/json; charset=utf-8",
        extra_headers={"etag": '"series-v1"'},
    )
    context = _context(worldbank.SOURCE_ID, tmp_path, "worldbank-run-1")

    artifact = worldbank.extract_indicator(
        "TEST.INDICATOR",
        context=context,
        adapter=adapter,
    )
    series = worldbank.parse_indicator_artifact(artifact, "TEST.INDICATOR")

    digest = hashlib.sha256(payload).hexdigest()
    assert artifact.envelope.content_hash == digest
    assert artifact.envelope.object_uri == f"raw-cache://{digest[:2]}/{digest}.json"
    assert artifact.envelope.native_id == "wb-TEST.INDICATOR-IND"
    assert artifact.envelope.pipeline_run_id == "worldbank-run-1"
    assert artifact.envelope.http_metadata["etag"] == '"series-v1"'
    assert json.loads(artifact.envelope.license_snapshot)["license"] == "CC-BY-4.0"
    assert (tmp_path / artifact.provenance_ref).read_bytes() == payload
    assert context.object_store.read(artifact.envelope.object_uri) == payload
    assert series.points == [(2022, 4.0), (2024, 7.5)]
    assert len(calls) == 1

    duplicate = worldbank.extract_indicator(
        "TEST.INDICATOR",
        context=context,
        adapter=adapter,
    )
    assert duplicate.envelope.envelope_id == artifact.envelope.envelope_id
    assert duplicate.envelope.object_uri == artifact.envelope.object_uri
    assert len(list(tmp_path.rglob("*.json"))) == 1


def test_myneta_crawl_adapter_uses_existing_candidate_parser(tmp_path: Path) -> None:
    payload = (FIXTURES / "myneta_candidate_5395.html").read_bytes()
    adapter, _calls = _http_adapter(payload, "text/html; charset=utf-8")
    context = _context(myneta.SOURCE_ID, tmp_path, "myneta-run-1")

    artifact = myneta.extract_candidate("5395", context=context, adapter=adapter)
    candidate = myneta.parse_candidate_artifact(artifact, "5395")

    assert artifact.envelope.source_id == "myneta.candidates"
    assert artifact.envelope.native_id == "LS2024:5395"
    assert artifact.provenance_ref.endswith(".html")
    assert candidate.name == "GODAM NAGESH"
    assert candidate.total_assets == 30_916_833


def test_myneta_discovery_endpoints_emit_distinct_raw_artifacts(tmp_path: Path) -> None:
    context = _context(myneta.SOURCE_ID, tmp_path, "myneta-discovery-run")
    winners_payload = (FIXTURES / "myneta_winners_ls2024.html").read_bytes()
    winners_adapter, winners_calls = _http_adapter(winners_payload, "text/html")

    winners_artifact = myneta.extract_winners(context=context, adapter=winners_adapter)
    winners = myneta.parse_winners_artifact(winners_artifact)

    assert winners
    assert winners_artifact.envelope.native_id == "LS2024:winners"
    assert winners_calls[0][1]["params"] == {"action": "show_winners", "sort": "default"}

    index_payload = (
        b'<a href="index.php?action=show_candidates&constituency_id=17">Example Seat (SC)</a>'
    )
    index_adapter, _calls = _http_adapter(index_payload, "text/html")
    index_artifact = myneta.extract_constituency_index(context=context, adapter=index_adapter)
    assert myneta.parse_constituency_map_artifact(index_artifact) == {"EXAMPLE SEAT": "17"}

    candidates_payload = b"""
      <a href="candidate.php?candidate_id=10">Example Candidate</a>&nbsp; Winner
      <a href="candidate.php?candidate_id=11">Other Candidate</a>
    """
    candidates_adapter, candidate_calls = _http_adapter(candidates_payload, "text/html")
    candidates_artifact = myneta.extract_constituency_candidates(
        "17",
        context=context,
        adapter=candidates_adapter,
    )
    assert myneta.parse_constituency_candidates_artifact(candidates_artifact) == [
        ("10", "Example Candidate"),
        ("11", "Other Candidate"),
    ]
    assert myneta.parse_constituency_winner_artifact(candidates_artifact) == "10"
    assert candidates_artifact.envelope.native_id == "LS2024:constituency:17"
    assert candidate_calls[0][1]["params"]["constituency_id"] == "17"
    assert len(list(tmp_path.rglob("*.html"))) == 3


def test_digital_sansad_member_pages_are_individually_enveloped(tmp_path: Path) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def get(url: str, **kwargs: object) -> httpx.Response:
        calls.append((url, kwargs))
        params = kwargs["params"]
        assert isinstance(params, dict)
        page = int(params["page"])
        payload = {
            "membersDtoList": [
                {
                    "mpsno": page,
                    "mpFirstLastName": f"Shri Member {page}",
                    "partySname": "EX",
                    "stateName": "Example State",
                    "constName": f"Seat {page}",
                    "email": f"member{page}[at]mpls[dot]sansad[dot]in",
                }
            ],
            "metaDatasDto": {"totalPages": 2},
        }
        return httpx.Response(
            200,
            json=payload,
            headers={"content-type": "application/json"},
            request=httpx.Request("GET", url),
        )

    context = _context(sansad.SOURCE_ID, tmp_path, "sansad-members-run")
    members = sansad.fetch_ls_sitting_members(
        page_size=1,
        context=context,
        adapter=HttpSourceAdapter(get=get),
    )

    assert [member.member_id for member in members] == ["1", "2"]
    assert all(member.raw_ref for member in members)
    assert members[0].official_email == "member1@mpls.sansad.in"
    assert len(calls) == 2
    assert len(list(tmp_path.rglob("*.json"))) == 2


def test_digital_sansad_rs_and_committee_adapters_preserve_source_responses(
    tmp_path: Path,
) -> None:
    member_payload = json.dumps(
        {
            "records": [
                {
                    "mpsno": "77",
                    "name": "Example, Smt Member",
                    "partyCode": "EX",
                    "state": "Nominated",
                    "term": "2024-2030",
                }
            ],
            "_metadata": {"totalPages": 1},
        }
    ).encode()
    member_adapter, _calls = _http_adapter(member_payload, "application/json")
    member_context = _context(sansad.SOURCE_ID, tmp_path / "members", "sansad-rs-run")
    member_artifact = sansad.extract_rs_members_page(
        1,
        100,
        context=member_context,
        adapter=member_adapter,
    )
    members, total_pages = sansad.parse_rs_members_page(member_artifact)
    assert total_pages == 1
    assert members[0].name == "Member Example"
    assert members[0].nominated is True
    assert members[0].state is None

    committee_payload = json.dumps(
        [
            {
                "committeeName": "Example Committee",
                "committeeType": "Standing",
                "committeeFormationDate": "2026-01-01",
                "memberOrChairperson": "Chairperson",
                "memberName": "Example, Shri Member",
                "memberHouse": "Lok sabha",
            }
        ]
    ).encode()
    committee_context = _context(
        sansad_committees.SOURCE_ID,
        tmp_path / "committees",
        "sansad-committee-run",
    )
    committee_adapter, _calls = _http_adapter(committee_payload, "application/json")
    committee_artifact = sansad_committees.extract_committee_members(
        9,
        context=committee_context,
        adapter=committee_adapter,
    )
    committee_members = sansad_committees.parse_committee_members_artifact(
        committee_artifact,
        9,
    )
    assert committee_members[0].member_name == "Member Example"
    assert committee_members[0].is_chairperson is True
    assert committee_members[0].raw_ref == committee_artifact.provenance_ref

    empty_adapter, _calls = _http_adapter(
        b"404 page not found",
        "text/plain",
        status_code=400,
    )
    empty_artifact = sansad_committees.extract_committee_members(
        10,
        context=committee_context,
        adapter=empty_adapter,
    )
    assert sansad_committees.parse_committee_members_artifact(empty_artifact, 10) == []
    assert empty_artifact.envelope.http_metadata["status_code"] == "400"


def test_prs_listing_and_profile_share_the_standard_adapter_boundary(tmp_path: Path) -> None:
    listing_payload = (FIXTURES / "prs_mptrack_ls_listing.html").read_bytes()
    listing_adapter, listing_calls = _http_adapter(listing_payload, "text/html; charset=utf-8")
    context = _context(prs.SOURCE_ID, tmp_path, "prs-run")

    roster = prs.fetch_roster("ls", context=context, adapter=listing_adapter)

    assert len(roster) == 9
    assert all(member.house == "ls" and member.raw_ref for member in roster)
    assert len(listing_calls) == 2
    assert listing_calls[0][1]["params"] == {"page": 1}
    assert listing_calls[1][1]["params"] == {"page": 2}

    profile_payload = (FIXTURES / "prs_mptrack_profile_tharoor.html").read_bytes()
    profile_adapter, _calls = _http_adapter(profile_payload, "text/html; charset=utf-8")
    profile_artifact = prs.extract_profile(
        roster[0],
        context=context,
        adapter=profile_adapter,
    )
    questions, debates = prs.parse_record_artifact(profile_artifact)

    assert prs.parse_attendance_artifact(profile_artifact) == 88.0
    assert prs.parse_report_period_artifact(profile_artifact) is not None
    assert len(questions) == 119
    assert len(debates) == 33
    assert profile_artifact.envelope.native_id.endswith(f":member:{roster[0].slug}:profile")


def test_roster_compatibility_command_routes_to_live_sansad_pipelines(monkeypatch) -> None:
    from neta_ingest.pipelines.lok_sabha import ls_roster, roster
    from neta_ingest.pipelines.rajya_sabha import rajya_sabha

    calls: list[str] = []
    monkeypatch.setattr(ls_roster, "run", lambda: calls.append("ls"))
    monkeypatch.setattr(rajya_sabha, "run", lambda: calls.append("rs"))

    roster.run("ls", "18")
    roster.run("rs", "current")

    assert calls == ["ls", "rs"]
    with pytest.raises(ValueError, match="supports cycle 18"):
        roster.run("ls", "17")


def test_google_news_feed_adapter_keeps_only_feed_metadata(tmp_path: Path) -> None:
    payload = b"""<?xml version="1.0" encoding="UTF-8"?>
    <rss><channel><item>
      <title>Member addresses Parliament - Example News</title>
      <link>https://example.test/story-1</link>
      <source>Example News</source>
      <pubDate>Thu, 30 Jul 2026 12:00:00 GMT</pubDate>
      <description>&lt;p&gt;Member addresses Parliament&lt;/p&gt;</description>
    </item></channel></rss>"""
    adapter, calls = _http_adapter(payload, "application/rss+xml")
    context = _context(google_news.SOURCE_ID, tmp_path, "news-run-1")

    artifact = google_news.extract_news(
        "Example Member",
        party="Example Party",
        slug="person-7",
        context=context,
        adapter=adapter,
    )
    articles = google_news.parse_news_artifact(artifact)

    assert artifact.envelope.native_id == "legislator:person-7"
    assert artifact.provenance_ref.endswith(".xml")
    assert len(articles) == 1
    assert articles[0].title == "Member addresses Parliament"
    assert articles[0].publisher == "Example News"
    assert articles[0].url == "https://example.test/story-1"
    assert calls[0][1]["headers"] == {"User-Agent": google_news._UA}


def test_adapter_rejects_a_manifest_from_another_source(tmp_path: Path) -> None:
    adapter, _calls = _http_adapter(b"{}", "application/json")
    wrong_context = _context(worldbank.SOURCE_ID, tmp_path)

    try:
        google_news.extract_news(
            "Example Member",
            context=wrong_context,
            adapter=adapter,
        )
    except ValueError as error:
        assert "does not match manifest" in str(error)
    else:
        raise AssertionError("cross-source execution must be rejected")


def test_raw_retention_policy_is_enforced_before_storage(tmp_path: Path) -> None:
    class RejectingStore:
        def put(self, payload: bytes, *, content_type: str):
            raise AssertionError("durable storage must not be called")

        def read(self, object_uri: str) -> bytes:
            raise AssertionError("there is no durable object to read")

    registered = _context(google_news.SOURCE_ID, tmp_path)
    no_retention_manifest = registered.manifest.model_copy(
        update={
            "rights": registered.manifest.rights.model_copy(update={"store_raw": False}),
        }
    )
    context = ExtractionContext(
        manifest=no_retention_manifest,
        pipeline_run_id="no-retention-run",
        object_store=RejectingStore(),
    )

    artifact = capture_raw(
        context=context,
        source_id=google_news.SOURCE_ID,
        native_id="legislator:7",
        source_uri="https://news.google.com/rss/search?q=example",
        payload=b"feed metadata",
        content_type="application/rss+xml",
    )

    assert artifact.provenance_ref is None
    assert artifact.envelope.object_uri.startswith("transient://news.google_feed/")
    assert json.loads(artifact.envelope.license_snapshot)["store_raw"] is False


def test_orchestration_scope_propagates_run_id_and_observes_artifacts(tmp_path: Path) -> None:
    observed = []
    with pipeline_execution_scope(
        "dagster:run-7",
        artifact_observer=lambda artifact: observed.append(artifact.envelope),
    ):
        context = source_extraction_context(
            worldbank.SOURCE_ID,
            object_store=FileRawObjectStore(tmp_path),
        )
        artifact = capture_raw(
            context=context,
            source_id=worldbank.SOURCE_ID,
            native_id="wb-TEST-IND",
            source_uri="https://api.worldbank.org/v2/example",
            payload=b"{}",
            content_type="application/json",
        )

    assert artifact.envelope.pipeline_run_id == "dagster:run-7"
    assert observed == [artifact.envelope]
