import typer
from anyio import run
from seed.lok_sabha_seed import LokSabhaSeed

app = typer.Typer()


@app.command()
def scrape_all_sansad_members():
    seeder = LokSabhaSeed()
    run(seeder.upsert_member_list)


if __name__ == "__main__":
    app()
