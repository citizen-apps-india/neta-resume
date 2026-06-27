"""Neta ingestion CLI.

    uv run neta roster      --house ls --cycle 18
    uv run neta affidavits  --house ls --cycle LS2024
    uv run neta criminal    --house ls --cycle LS2024
    uv run neta resolve
    uv run neta party-switch

Each command is a thin wrapper around a pipeline in neta_ingest.pipelines. Pipelines are idempotent
(upsert on natural keys), so re-running is always safe.
"""

from __future__ import annotations

import typer

app = typer.Typer(help="Neta-Resume ingestion pipelines", no_args_is_help=True)


@app.command()
def roster(house: str = "ls", cycle: str = "18") -> None:
    """Fetch the legislature roster (sansad.in) -> office_term + source_ref."""
    from neta_ingest.pipelines import roster as p

    p.run(house=house, cycle=cycle)


@app.command()
def myneta(house: str = "ls", cycle: str = "LS2024", limit: int = 10,
           candidate: list[str] = typer.Option(None, help="specific candidate_id(s) to ingest")) -> None:
    """Ingest full MyNeta candidates (wealth + criminal in one pass) -> person + affidavit + cases."""
    from neta_ingest.pipelines import myneta as p

    p.run(house=house, cycle=cycle, limit=limit, candidate_ids=candidate or None)


# MyNeta serves wealth + criminal on one page, so both commands run the same unified (idempotent) ingest.
@app.command()
def affidavits(house: str = "ls", cycle: str = "LS2024", limit: int = 10) -> None:
    """Fetch ECI affidavit wealth via MyNeta -> affidavit (+ criminal, same page)."""
    from neta_ingest.pipelines import myneta as p

    p.run(house=house, cycle=cycle, limit=limit)


@app.command()
def criminal(house: str = "ls", cycle: str = "LS2024", limit: int = 10) -> None:
    """Fetch declared criminal cases via MyNeta -> criminal_case + charges (+ severity)."""
    from neta_ingest.pipelines import myneta as p

    p.run(house=house, cycle=cycle, limit=limit)


@app.command()
def resolve() -> None:
    """Entity-resolve unresolved source_refs to canonical persons."""
    from neta_ingest.pipelines import resolve_persons as p

    p.run()


@app.command(name="party-switch")
def party_switch() -> None:
    """Diff office_term party across cycles -> party_affiliation + party_switch_event."""
    from neta_ingest.pipelines import party_switch as p

    p.run()


if __name__ == "__main__":
    app()
