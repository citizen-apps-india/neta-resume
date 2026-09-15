"""Private FastAPI control-plane entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from neta_backend.admin.routes import admin_api_router, admin_page_router
from neta_backend.config import BackendSettings, settings

STATIC_DIRECTORY = Path(__file__).parent / "admin" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app_settings: BackendSettings = app.state.settings
    engine_options: dict[str, object] = {
        "echo": app_settings.sql_echo,
    }
    if not app_settings.database_url.startswith("sqlite"):
        # poolclass=NullPool: open a connection per request and close it for real when the request
        # ends, rather than holding one open for the life of the process.
        #
        # This mirrors the fix applied to api/neta_api/deps.py in #106, for the same reason. Neon's
        # serverless compute only stops billing CU-hours when it has ZERO connections — idle counts
        # the same as busy — so a single pooled connection held by a long-lived process keeps the
        # meter running 24/7 regardless of query volume. That is what drove the free-tier meter to
        # ~95/100 CU-hrs and exhausted the quota mid-migration in July. This service is about to
        # become a second long-lived consumer of the same database, so it must not repeat it.
        #
        # pool_size / max_overflow are deliberately not passed: they configure QueuePool, which
        # NullPool replaces. The settings remain in config.py for a future deployment shape that
        # genuinely wants pooling (a dedicated instance, or a non-serverless Postgres).
        #
        # Trade-off: every request pays a fresh connection handshake, and a request landing after
        # Neon has suspended pays a cold start on top. Right trade for a low-traffic admin console.
        engine_options["poolclass"] = NullPool
    engine = create_async_engine(
        app_settings.database_url,
        **engine_options,
    )
    app.state.db_engine = engine
    app.state.db_sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield
    finally:
        await engine.dispose()


def create_app(app_settings: BackendSettings | None = None) -> FastAPI:
    configured_settings = app_settings or settings
    application = FastAPI(
        title="Neta-Resume Control API",
        version="0.2.0",
        description="Private, authenticated ingestion control and execution API.",
        lifespan=lifespan,
    )
    application.state.settings = configured_settings
    application.mount(
        "/admin/static",
        StaticFiles(directory=STATIC_DIRECTORY),
        name="admin-static",
    )
    application.include_router(admin_page_router)
    application.include_router(admin_api_router)

    @application.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
