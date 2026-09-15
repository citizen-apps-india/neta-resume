"""Bounding + resumability guarantees for the news enrichment pipeline.

Context: the `news` GitHub Actions workflow used to have no per-run bound and no `timeout-minutes`,
so a run that hit slow/throttled responses from Google News (very plausible from shared CI IPs) had
no way to stop itself and was hard-cancelled by GitHub's own 360-minute ceiling every time. These tests
exercise the fix's two load-bearing pieces without any real network or database access:

  1. `_time_budget_exceeded` — the pure wall-clock check that lets a run stop itself.
  2. `run()` — wired end-to-end (roster query, per-person fetch, DB writes) against fakes, proving
     that once the budget is spent the loop stops cleanly, logs what it did and what's left, and never
     touches the untouched rows.
"""

from __future__ import annotations

from types import SimpleNamespace

from neta_ingest.pipelines.enrich import news


def test_time_budget_exceeded_is_a_pure_clock_check() -> None:
    started = 1_000.0
    assert not news._time_budget_exceeded(started, now=started)
    assert not news._time_budget_exceeded(started, now=started + news.TIME_BUDGET_SECONDS - 1)
    assert news._time_budget_exceeded(started, now=started + news.TIME_BUDGET_SECONDS)
    assert news._time_budget_exceeded(started, now=started + news.TIME_BUDGET_SECONDS + 1)


def _row(pid: int, name: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=pid,
        display_name=name,
        normalized_name=name.lower(),
        party="INC",
        constituency="Test",
        house_code="ls",
    )


class _FakeResult:
    def __init__(self, rows: list) -> None:
        self._rows = rows

    def all(self) -> list:
        return self._rows


class _FakeSession:
    """Just enough of the Session surface for news.run(): roster SELECT, DELETE, INSERT."""

    def __init__(self, roster: list) -> None:
        self._roster = roster
        self.deleted_person_ids: list[int] = []
        self.inserted: list[dict] = []

    def execute(self, stmt, params: dict | None = None):
        sql = str(stmt)
        if "FROM person p" in sql:
            return _FakeResult(self._roster)
        if sql.strip().startswith("DELETE FROM news_item"):
            self.deleted_person_ids.append(params["p"])
            return _FakeResult([])
        if sql.strip().startswith("INSERT INTO news_item"):
            self.inserted.append(params)
            return _FakeResult([])
        raise AssertionError(f"unexpected statement in test: {sql!r}")


class _FakeScope:
    """A `session_scope()` stand-in that always hands back the same fake session."""

    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    def __call__(self):
        return self

    def __enter__(self) -> _FakeSession:
        return self._session

    def __exit__(self, *exc_info: object) -> bool:
        return False


def test_run_stops_cleanly_once_the_time_budget_is_spent(monkeypatch, capsys) -> None:
    roster = [_row(i, f"Person {i}") for i in range(5)]
    session = _FakeSession(roster)
    scope = _FakeScope(session)

    monkeypatch.setattr(news, "session_scope", scope)
    monkeypatch.setattr(news, "record_source_ref", lambda *a, **k: 1)
    monkeypatch.setattr(news, "source_extraction_context", lambda *a, **k: object())
    monkeypatch.setattr(news.gn, "extract_news", lambda *a, **k: SimpleNamespace(provenance_ref=None))
    monkeypatch.setattr(news.gn, "parse_news_artifact", lambda artifact: [])

    # Clock reads: one call for `started`, then one budget check per loop iteration attempted.
    # In-budget for the first legislator, over budget from the second check onward — so the loop
    # must process exactly 1 of 5 and stop.
    ticks = iter([0.0, 0.0, news.TIME_BUDGET_SECONDS + 1, news.TIME_BUDGET_SECONDS + 1])
    monkeypatch.setattr(news, "_clock", lambda: next(ticks))

    news.run()

    out = capsys.readouterr().out
    assert "stopping cleanly with 4 legislators left" in out
    # Only the one legislator processed before the budget tripped got touched.
    assert session.deleted_person_ids == [0]
    assert "done:" not in out  # the early-stop path, not the normal-completion summary


def test_run_reports_normal_completion_when_budget_is_not_exceeded(monkeypatch, capsys) -> None:
    roster = [_row(1, "Person One")]
    session = _FakeSession(roster)
    scope = _FakeScope(session)

    monkeypatch.setattr(news, "session_scope", scope)
    monkeypatch.setattr(news, "record_source_ref", lambda *a, **k: 1)
    monkeypatch.setattr(news, "source_extraction_context", lambda *a, **k: object())
    monkeypatch.setattr(news.gn, "extract_news", lambda *a, **k: SimpleNamespace(provenance_ref=None))
    monkeypatch.setattr(news.gn, "parse_news_artifact", lambda artifact: [])
    monkeypatch.setattr(news, "_clock", lambda: 0.0)

    news.run()

    out = capsys.readouterr().out
    assert "done: 1 legislators" in out
    assert "Nothing left in this run's batch" in out
    assert session.deleted_person_ids == [1]
