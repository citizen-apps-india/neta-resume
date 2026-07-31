"""dlt-backed catalog of immutable raw-envelope metadata."""

from __future__ import annotations

from dataclasses import dataclass
from tempfile import TemporaryDirectory

import dagster as dg
import dlt

from neta_core.pipeline import RawEnvelope


@dataclass(frozen=True, slots=True)
class HistoryLoadResult:
    envelope_count: int
    load_ids: tuple[str, ...] = ()


class DltHistoryResource(dg.ConfigurableResource):
    """Schema-aware envelope ledger in a dlt-owned PostgreSQL schema."""

    database_url: str
    dataset_name: str = "ingestion_history"

    def load(
        self,
        source_id: str,
        envelopes: list[RawEnvelope],
    ) -> HistoryLoadResult:
        unique = {envelope.envelope_id: envelope for envelope in envelopes}
        if not unique:
            return HistoryLoadResult(envelope_count=0)

        rows = [
            envelope.model_dump(mode="json", exclude_none=True)
            for envelope in unique.values()
        ]
        resource = dlt.resource(
            rows,
            name="raw_envelopes",
            primary_key="envelope_id",
            write_disposition="merge",
            schema_contract="evolve",
            max_table_nesting=0,
        )
        with TemporaryDirectory(prefix="neta-dlt-") as pipelines_dir:
            pipeline = dlt.pipeline(
                pipeline_name=f"neta_raw_history_{_slug(source_id)}",
                pipelines_dir=pipelines_dir,
                destination=dlt.destinations.postgres(
                    credentials=_postgres_database_url(self.database_url)
                ),
                dataset_name=self.dataset_name,
            )
            load_info = pipeline.run(resource)
        return HistoryLoadResult(
            envelope_count=len(rows),
            load_ids=tuple(load_info.loads_ids),
        )


def _postgres_database_url(database_url: str) -> str:
    return (
        database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        .replace("postgresql+psycopg2://", "postgresql://", 1)
        .replace("postgresql+psycopg://", "postgresql://", 1)
    )


def _slug(value: str) -> str:
    return value.replace(".", "_").replace("-", "_")
