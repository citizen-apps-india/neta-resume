"""The photo proxy must serve a disk-cache hit without touching the database (Neon wakes on connect)."""

from __future__ import annotations

import urllib.request
from pathlib import Path

import pytest
from fastapi import HTTPException

from neta_api.routers import persons


class _ForbiddenDb:
    def execute(self, *a, **k):  # pragma: no cover - failing path
        raise AssertionError("database touched")


class _Db:
    def __init__(self, url: str | None) -> None:
        self.url, self.calls = url, 0

    def execute(self, *a, **k):
        self.calls += 1
        return type("R", (), {"scalar": lambda _s: self.url})()


@pytest.fixture
def cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(persons, "_PHOTO_CACHE", tmp_path)
    return tmp_path


def test_cache_hit_never_touches_the_database(cache: Path) -> None:
    (cache / "7.jpg").write_bytes(b"jpegbytes")
    r = persons.person_photo(7, _ForbiddenDb())
    assert r.body == b"jpegbytes"
    assert "max-age=604800" in r.headers["cache-control"]
    assert r.headers["cross-origin-resource-policy"] == "cross-origin"


def test_cache_hit_opens_no_connection(cache: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from neta_api import deps

    def boom(*a, **k):
        raise AssertionError("connection opened")

    monkeypatch.setattr(deps.engine.pool, "connect", boom, raising=False)
    db = deps.SessionLocal()
    (cache / "8.jpg").write_bytes(b"x")
    try:
        assert persons.person_photo(8, db).body == b"x"
    finally:
        db.close()


def test_miss_queries_then_fetches_and_caches(cache: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class _Resp:
        headers: dict = {}

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self, n):
            return b"fresh"

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: _Resp())
    db = _Db("https://sansad.in/p.jpg")
    assert persons.person_photo(9, db).body == b"fresh"
    assert db.calls == 1 and (cache / "9.jpg").read_bytes() == b"fresh"
    assert persons.person_photo(9, _ForbiddenDb()).body == b"fresh"


def test_miss_without_photo_is_404(cache: Path) -> None:
    with pytest.raises(HTTPException) as e:
        persons.person_photo(1, _Db(None))
    assert e.value.status_code == 404


def test_miss_rejects_disallowed_host_before_fetching(cache: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("fetched")))
    with pytest.raises(HTTPException) as e:
        persons.person_photo(2, _Db("https://evil.example/p.jpg"))
    assert e.value.status_code == 400
    assert not (cache / "2.jpg").exists()
