"""The PDF proxy must serve a disk-cache hit without touching the database (Neon wakes on connect)."""

from __future__ import annotations

import urllib.request
from pathlib import Path

import pytest
from fastapi import HTTPException

from neta_api.diskcache import write_atomic
from neta_api.routers import questions


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
    monkeypatch.setattr(questions, "_DOC_CACHE", tmp_path)
    return tmp_path


def test_cache_hit_never_touches_the_database(cache: Path) -> None:
    (cache / "question-5.pdf").write_bytes(b"%PDF-cached")
    r = questions._serve_document("question", 5, _ForbiddenDb())
    assert r.body == b"%PDF-cached"
    assert r.media_type == "application/pdf"


def test_cache_hit_opens_no_connection(cache: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from neta_api import deps

    def boom(*a, **k):
        raise AssertionError("connection opened")

    monkeypatch.setattr(deps.engine.pool, "connect", boom, raising=False)
    db = deps.SessionLocal()
    (cache / "debate-6.pdf").write_bytes(b"%PDF-x")
    try:
        assert questions._serve_document("debate", 6, db).body == b"%PDF-x"
    finally:
        db.close()


def test_miss_queries_once_then_fetches_and_caches(cache: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self, n):
            return b"%PDF-fresh"

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: _Resp())
    db = _Db("https://sansad.in/getFile/x.pdf")
    assert questions._serve_document("question", 9, db).body == b"%PDF-fresh"
    assert db.calls == 1 and (cache / "question-9.pdf").read_bytes() == b"%PDF-fresh"
    assert questions._serve_document("question", 9, _ForbiddenDb()).body == b"%PDF-fresh"


def test_miss_without_document_is_404(cache: Path) -> None:
    with pytest.raises(HTTPException) as e:
        questions._serve_document("question", 1, _Db(None))
    assert e.value.status_code == 404


def test_miss_with_disallowed_host_is_unavailable_and_not_fetched(cache: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("fetched")))
    r = questions._serve_document("question", 2, _Db("https://evil.example/getFile/x.pdf"))
    assert b"temporarily unavailable" in r.body
    assert not (cache / "question-2.pdf").exists()


def test_write_atomic_leaves_no_temp_file_and_replaces(tmp_path: Path) -> None:
    target = tmp_path / "a.bin"
    write_atomic(target, b"one")
    write_atomic(target, b"two")
    assert target.read_bytes() == b"two"
    assert [p.name for p in tmp_path.iterdir()] == ["a.bin"]
