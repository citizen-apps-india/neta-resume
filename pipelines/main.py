import typer
from anyio import run
from seed.lok_sabha_seed import LokSabhaSeed
from workflows.tasks.scraper_tasks import GoogleTaskExecutor

app = typer.Typer()


@app.command()
def scrape_all_sansad_members():
    seeder = LokSabhaSeed()
    run(seeder.upsert_member_list)


@app.command()
def add_scrape_task_jobs():
    gtask_executor = GoogleTaskExecutor()
    run(gtask_executor.upsert_pipeline_job)


@app.command()
def sync_local_secrets():
    from scripts.gcp_secret_sync import GCPSecretSync

    run(GCPSecretSync().sync_local_secrets_to_gcp)


if __name__ == "__main__":
    app()
