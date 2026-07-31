"""Validated orchestration entrypoints for manifest-backed ingestion sources.

Dagster passes only the JSON parameters captured on a ``pipeline_run``.  These wrappers reject
unknown values before calling the existing idempotent pipelines, keeping manual runs and backfills
reviewable while the source-specific parsing and canonical writes remain in their current modules.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from neta_ingest.pipelines.enrich import activity, attendance, committees, news
from neta_ingest.pipelines.enrich import parliamentary_record as record
from neta_ingest.pipelines.identity import myneta
from neta_ingest.pipelines.lok_sabha import ls_roster
from neta_ingest.pipelines.macro import indicators
from neta_ingest.pipelines.rajya_sabha import rajya_sabha


class RunnerParameters(BaseModel):
    """Strict base for operator-supplied run/backfill parameters."""

    model_config = ConfigDict(extra="forbid")


class DigitalSansadMemberParameters(RunnerParameters):
    house: Literal["ls", "rs", "all"] = "all"


class CommitteeParameters(RunnerParameters):
    loksabha: int = Field(default=18, ge=1)
    limit: int | None = Field(default=None, ge=1)


class MyNetaParameters(RunnerParameters):
    cycle: str = Field(default="LS2024", min_length=1)
    house: str = Field(default="ls", min_length=1)
    limit: int = 0
    candidate_ids: list[str] | None = None


class NewsParameters(RunnerParameters):
    house: Literal["ls", "rs"] | None = None
    limit: int | None = Field(default=None, ge=1)


class PrsParameters(RunnerParameters):
    houses: list[Literal["ls", "rs"]] = Field(default_factory=lambda: ["ls", "rs"])
    operations: list[Literal["attendance", "activity", "record"]] = Field(
        default_factory=lambda: ["attendance", "activity", "record"]
    )


class WorldBankParameters(RunnerParameters):
    indicators: list[str] | None = None


def run_digital_sansad_members(parameters: Mapping[str, Any]) -> None:
    parsed = DigitalSansadMemberParameters.model_validate(parameters)
    if parsed.house in {"ls", "all"}:
        ls_roster.run()
    if parsed.house in {"rs", "all"}:
        rajya_sabha.run()


def run_digital_sansad_committees(parameters: Mapping[str, Any]) -> None:
    parsed = CommitteeParameters.model_validate(parameters)
    committees.run(loksabha=parsed.loksabha, limit=parsed.limit)


def run_myneta_candidates(parameters: Mapping[str, Any]) -> None:
    parsed = MyNetaParameters.model_validate(parameters)
    myneta.run(
        cycle=parsed.cycle,
        house=parsed.house,
        limit=parsed.limit,
        candidate_ids=parsed.candidate_ids,
    )


def run_news_feed(parameters: Mapping[str, Any]) -> None:
    parsed = NewsParameters.model_validate(parameters)
    news.run(house=parsed.house, limit=parsed.limit)


def run_prs_parliamentary_record(parameters: Mapping[str, Any]) -> None:
    parsed = PrsParameters.model_validate(parameters)
    for house in parsed.houses:
        if "attendance" in parsed.operations:
            attendance.run(house=house)
        if "activity" in parsed.operations:
            activity.run(house=house)
        if "record" in parsed.operations:
            record.run(house=house)


def run_worldbank_indicators(parameters: Mapping[str, Any]) -> None:
    parsed = WorldBankParameters.model_validate(parameters)
    indicators.run(only=parsed.indicators)
