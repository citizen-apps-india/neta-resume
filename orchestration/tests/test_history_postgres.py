from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, text

from neta_core.pipeline import RawEnvelope
from neta_orchestration.history import DltHistoryResource

DATABASE_URL = os.getenv("NETA_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    DATABASE_URL is None,
    reason="NETA_TEST_DATABASE_URL is required for PostgreSQL integration tests",
)


def test_dlt_merges_envelope_history_by_content_identity() -> None:
    assert DATABASE_URL is not None
    envelope = RawEnvelope(
        envelope_id=f"test.source:item:{'a' * 64}",
        source_id="test.source",
        native_id="item",
        source_uri="https://example.test/item",
        fetched_at=datetime(2026, 7, 31, tzinfo=UTC),
        content_type="application/json",
        content_hash="a" * 64,
        object_uri="raw-cache://aa/item.json",
        license_snapshot="test-only",
        pipeline_run_id="pipeline-run-1",
    )
    loader = DltHistoryResource(database_url=DATABASE_URL)

    first = loader.load(envelope.source_id, [envelope, envelope])
    second = loader.load(envelope.source_id, [envelope])

    assert first.envelope_count == second.envelope_count == 1
    engine = create_engine(_sync_database_url(DATABASE_URL))
    try:
        with engine.connect() as connection:
            count = connection.scalar(
                text(
                    "SELECT count(*) FROM ingestion_history.raw_envelopes "
                    "WHERE envelope_id = :envelope_id"
                ),
                {"envelope_id": envelope.envelope_id},
            )
        assert count == 1
    finally:
        engine.dispose()


def _sync_database_url(database_url: str) -> str:
    return (
        database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
        .replace("postgresql://", "postgresql+psycopg://", 1)
    )
