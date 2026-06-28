"""FastAPI app entrypoint.

    uv run uvicorn neta_api.main:app --reload

OpenAPI at /docs. The frontend codegens its TS types from /openapi.json.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from neta_api.deps import settings
from neta_api.routers import persons, search, stats, visits

app = FastAPI(
    title="Neta-Resume API",
    version="0.1.0",
    description="Read-only resume aggregate for Indian legislators. Every fact carries provenance.",
)

# Allowed origins are env-driven (NETA_ALLOWED_ORIGINS); the default is the local Next.js dev server.
# Read-only API, so GET only and no credentials.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(persons.router)
app.include_router(search.router)
app.include_router(stats.router)
app.include_router(visits.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
