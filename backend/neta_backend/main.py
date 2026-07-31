"""Private FastAPI control-plane entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from neta_backend.admin.routes import admin_api_router, admin_page_router
from neta_backend.config import BackendSettings, settings

STATIC_DIRECTORY = Path(__file__).parent / "admin" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app_settings: BackendSettings = app.state.settings
    engine_options: dict[str, object] = {
        "echo": app_settings.sql_echo,
        "pool_pre_ping": True,
    }
    if not app_settings.database_url.startswith("sqlite"):
        engine_options.update(
            pool_size=app_settings.pool_size,
            max_overflow=app_settings.max_overflow,
        )
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
