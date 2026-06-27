"""FastAPI app entrypoint.

    uv run uvicorn neta_api.main:app --reload

OpenAPI at /docs. The frontend codegens its TS types from /openapi.json.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from neta_api.routers import persons, search

app = FastAPI(
    title="Neta-Resume API",
    version="0.1.0",
    description="Read-only resume aggregate for Indian legislators. Every fact carries provenance.",
)

# Dev: allow the Next.js dev server. Tighten for any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(persons.router)
app.include_router(search.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
