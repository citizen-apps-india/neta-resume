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
def migrate(dir: str = "db/migrations",
            baseline: bool = typer.Option(False, help="record existing files as applied WITHOUT running "
                                          "them (one-time adoption on an already-populated DB)")) -> None:
    """Apply pending schema migrations (version-tracked in schema_migrations). Uses the owner DSN."""
    from neta_ingest import admin

    admin.run_migrate(dir=dir, baseline=baseline)


@app.command()
def seed(dir: str = "db/seeds") -> None:
    """(Re-)apply the idempotent reference seeds (houses, sources, parties, …) + the state registry."""
    from neta_ingest import admin

    admin.run_seed(dir=dir)


@app.command(name="seed-states")
def seed_states() -> None:
    """Upsert state/UT assembly house + term_cycle rows from the elections registry (idempotent)."""
    from neta_ingest import admin

    admin.run_seed_states()


@app.command()
def roster(house: str = "ls", cycle: str = "18") -> None:
    """Fetch the legislature roster (sansad.in) -> office_term + source_ref."""
    from neta_ingest.pipelines.lok_sabha import roster as p

    p.run(house=house, cycle=cycle)


@app.command()
def myneta(house: str = "ls", cycle: str = "LS2024", limit: int = 10,
           candidate: list[str] = typer.Option(None, help="specific candidate_id(s) to ingest")) -> None:
    """Ingest full MyNeta candidates (wealth + criminal in one pass) -> person + affidavit + cases."""
    from neta_ingest.pipelines.identity import myneta as p

    p.run(house=house, cycle=cycle, limit=limit, candidate_ids=candidate or None)


# MyNeta serves wealth + criminal on one page, so both commands run the same unified (idempotent) ingest.
@app.command()
def affidavits(house: str = "ls", cycle: str = "LS2024", limit: int = 10) -> None:
    """Fetch ECI affidavit wealth via MyNeta -> affidavit (+ criminal, same page)."""
    from neta_ingest.pipelines.identity import myneta as p

    p.run(house=house, cycle=cycle, limit=limit)


@app.command()
def criminal(house: str = "ls", cycle: str = "LS2024", limit: int = 10) -> None:
    """Fetch declared criminal cases via MyNeta -> criminal_case + charges (+ severity)."""
    from neta_ingest.pipelines.identity import myneta as p

    p.run(house=house, cycle=cycle, limit=limit)


@app.command()
def resolve() -> None:
    """Entity-resolve unresolved source_refs to canonical persons."""
    from neta_ingest.pipelines.identity import resolve_persons as p

    p.run()


@app.command(name="enrich-missing")
def enrich_missing(cycle: str = "LS2024") -> None:
    """Backfill affidavit data for LS members MyNeta omitted from its winners list (per-constituency)."""
    from neta_ingest.pipelines.lok_sabha import enrich_missing_affidavits as p

    p.run(cycle=cycle)


@app.command(name="historical-lookup")
def historical_lookup(cycle: str,
                      house: str = typer.Option("ls", help="house code: ls|mh_vs|… (current roster's house)"),
                      current_cycle: str = typer.Option("LS2024", help="the current cycle to backfill from"),
                      limit: int = typer.Option(None, help="cap members processed (testing)"),
                      refresh_index: bool = typer.Option(False, help="re-crawl the cycle candidate index")) -> None:
    """Tier-2: find sitting members' PAST-cycle candidacies (even losses/seat changes) and attach affidavits.

    cycle is a PAST cycle (e.g. LS2019|LS2014|LS2009, or MH_VS2019|MH_VS2014|MH_VS2009 with
    --house mh_vs --current-cycle MH_VS2024). Confident matches are written; ambiguous ones are
    queued to data/hist_index/review_<cycle>.json.
    """
    from neta_ingest.pipelines.lok_sabha import historical_lookup as p

    p.run(cycle=cycle, current_cycle=current_cycle, house=house, limit=limit, refresh_index=refresh_index)


@app.command(name="ls-roster")
def ls_roster() -> None:
    """Complete the Lok Sabha roster + official photos from sansad.in (fill + add missing members)."""
    from neta_ingest.pipelines.lok_sabha import ls_roster as p

    p.run()


@app.command(name="rajya-sabha")
def rajya_sabha() -> None:
    """Ingest the sitting Rajya Sabha roster from sansad.in (roster + photo; no affidavit data)."""
    from neta_ingest.pipelines.rajya_sabha import rajya_sabha as p

    p.run()


@app.command()
def attendance(house: str = "ls") -> None:
    """Attach cumulative parliamentary attendance % (PRS) to current-term office_terms. house: ls|rs."""
    from neta_ingest.pipelines.enrich import attendance as p

    p.run(house=house)


@app.command(name="native-names")
def native_names() -> None:
    """Backfill Devanagari (Hindi) names from Wikidata for the 18th Lok Sabha."""
    from neta_ingest.pipelines.enrich import native_names as p

    p.run()


@app.command(name="enrich-switches")
def enrich_switches() -> None:
    """Attach sourced 'why' narratives to detected party-switch events."""
    from neta_ingest.pipelines.enrich import enrich_switches as p

    p.run()


@app.command(name="canon-parties")
def canon_parties() -> None:
    """Merge abbreviation/full-name duplicate party records and clear resulting false switches."""
    from neta_ingest.pipelines.identity import canon_parties as p

    p.run()


@app.command(name="merge-cycles")
def merge_cycles() -> None:
    """Merge the same person across election cycles (incumbents) and detect party switches."""
    from neta_ingest.pipelines.identity import merge_cycles as p

    p.run()


@app.command(name="news")
def news(house: str = typer.Option(None, help="ls|rs (default: both)"),
         limit: int = typer.Option(None, help="cap legislators processed (testing)")) -> None:
    """Scrape recent Google News coverage for sitting legislators -> news_item."""
    from neta_ingest.pipelines.enrich import news as p

    p.run(house=house, limit=limit)


@app.command(name="contacts")
def contacts(house: str = typer.Option(None, help="ls|rs (default: both)")) -> None:
    """Attach official contact channels (email/office phone/profile) to sitting MPs from sansad.in."""
    from neta_ingest.pipelines.enrich import contacts as p

    p.run(house=house)


@app.command(name="leadership")
def leadership() -> None:
    """Seed marquee 18th-LS leadership roles (PM, Speaker, LoP, senior ministers) -> role."""
    from neta_ingest.pipelines.enrich import leadership as p

    p.run()


@app.command(name="fill-assembly")
def fill_assembly(house: str = "mh_vs", cycle: str = "MH_VS2024") -> None:
    """Backfill state-assembly winners MyNeta omits from its show_winners list (per-constituency)."""
    from neta_ingest.pipelines.state import assembly_backfill as p

    p.run(house=house, cycle=cycle)


@app.command(name="onboard-state")
def onboard_state(house: str,
                  cycle: str = typer.Option(None, help="ingest ONLY this cycle (to chunk a large state)"),
                  backfill: bool = typer.Option(False, help="also run historical-lookup (extra recall; "
                                                "expensive extra crawl)")) -> None:
    """Onboard a registered state assembly: ingest its cycles (myneta+fill), link across cycles + detect
    party switches. `--house up_vs`; the state's cycles come from the elections registry."""
    from neta_ingest.pipelines.state import onboard as p

    p.run(house=house, cycle=cycle, backfill=backfill)


@app.command(name="party-switch")
def party_switch() -> None:
    """Diff office_term party across cycles -> party_affiliation + party_switch_event."""
    from neta_ingest.pipelines.identity import party_switch as p

    p.run()


if __name__ == "__main__":
    app()
