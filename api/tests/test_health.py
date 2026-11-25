"""/health never opens a connection; /health/db is the one that does, and fails closed with 503."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from neta_api import deps
from neta_api.main import app


def test_health_opens_no_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*a, **k):
        raise AssertionError("connection opened")

    monkeypatch.setattr(deps.engine.pool, "connect", boom, raising=False)
    r = TestClient(app).get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_health_db_is_503_when_the_database_is_down() -> None:
    class _Down:
        def execute(self, *a, **k):
            raise RuntimeError("quota exceeded")

    app.dependency_overrides[deps.get_db] = lambda: _Down()
    try:
        r = TestClient(app).get("/health/db")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 503
