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
def affidavits(house: str = "ls", cycle: str = "LS2024") -> None:
    """Fetch ECI affidavit wealth via MyNeta -> affidavit + line items."""
    from neta_ingest.pipelines import affidavits as p

    p.run(house=house, cycle=cycle)


@app.command()
def criminal(house: str = "ls", cycle: str = "LS2024") -> None:
    """Fetch declared criminal cases via MyNeta -> criminal_case + charges (+ severity)."""
    from neta_ingest.pipelines import criminal as p

    p.run(house=house, cycle=cycle)


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
