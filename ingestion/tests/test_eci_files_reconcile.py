"""scripts/eci_files_reconcile.py isn't part of any package (it's a root-level script), so it's loaded
here by file path. Covers both halves: building entries/ from research files, and — redesign spec 1d —
applying data/eci_files/merges.json when present."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "eci_files_reconcile.py"
_spec = importlib.util.spec_from_file_location("eci_files_reconcile", _SCRIPT)
reconcile = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(reconcile)


def _entry(entry_id: str, *, sources: list[dict], verdict: str = "confirmed", date: str = "2025-01-01") -> dict:
    return {
        "id": entry_id,
        "kind": "event",
        "date": date,
        "date_precision": "day",
        "title": f"Entry {entry_id}",
        "summary": "A neutral summary.",
        "status": "documented",
        "sources": sources,
        "verification": {
            "verdict": verdict,
            "checked_url": sources[0]["url"] if sources else None,
            "note": "n/a",
        },
    }


def _setup(tmp_path: Path, *, research: dict[str, dict], merges: dict | None) -> None:
    research_dir = tmp_path / "research"
    entries_dir = tmp_path / "entries"
    research_dir.mkdir()
    for name, payload in research.items():
        (research_dir / name).write_text(json.dumps(payload))
    reconcile.RESEARCH = research_dir
    reconcile.ENTRIES = entries_dir
    reconcile.MERGES = tmp_path / "merges.json"
    if merges is not None:
        reconcile.MERGES.write_text(json.dumps(merges))


def test_builds_entries_from_research_area(tmp_path: Path) -> None:
    _setup(
        tmp_path,
        research={
            "numbers.json": {
                "area": "numbers",
                "entries": [_entry("n-1", sources=[{"url": "https://example.com/a", "tier": 1}])],
                "gaps": [],
            }
        },
        merges=None,
    )
    assert reconcile.main() == 0
    out = json.loads((reconcile.ENTRIES / "numbers.json").read_text())
    assert out["area"] == "numbers"
    assert [e["id"] for e in out["entries"]] == ["n-1"]
    assert out["entries"][0]["check"] == "checked"


def test_wrong_verdict_and_no_sources_are_excluded(tmp_path: Path) -> None:
    _setup(
        tmp_path,
        research={
            "numbers.json": {
                "area": "numbers",
                "entries": [
                    _entry("n-wrong", sources=[{"url": "https://example.com/a", "tier": 1}], verdict="wrong"),
                    _entry("n-no-sources", sources=[]),
                ],
                "gaps": [],
            }
        },
        merges=None,
    )
    reconcile.main()
    out = json.loads((reconcile.ENTRIES / "numbers.json").read_text())
    assert out["entries"] == []


def test_merge_marks_drop_ids_excluded_and_moves_citations_to_keep(tmp_path: Path) -> None:
    _setup(
        tmp_path,
        research={
            "numbers.json": {
                "area": "numbers",
                "entries": [
                    _entry("keep-1", sources=[{"url": "https://a.example/1", "tier": 1}]),
                ],
                "gaps": [],
            },
            "officials.json": {
                "area": "officials",
                "entries": [
                    _entry("drop-1", sources=[
                        {"url": "https://a.example/1", "tier": 1},  # duplicate of keep-1's url
                        {"url": "https://b.example/2", "tier": 3},
                    ]),
                ],
                "gaps": [],
            },
        },
        merges={"merges": [{"keep": "keep-1", "drop": ["drop-1"], "reason": "same event"}]},
    )
    reconcile.main()

    numbers = json.loads((reconcile.ENTRIES / "numbers.json").read_text())
    officials = json.loads((reconcile.ENTRIES / "officials.json").read_text())

    keep_entry = next(e for e in numbers["entries"] if e["id"] == "keep-1")
    drop_entry = next(e for e in officials["entries"] if e["id"] == "drop-1")

    assert drop_entry["exclude"] is True
    urls = [s["url"] for s in keep_entry["sources"]]
    assert urls == ["https://a.example/1", "https://b.example/2"]  # deduped, no repeat of the shared url


def test_merge_is_a_noop_when_merges_file_is_absent(tmp_path: Path) -> None:
    _setup(
        tmp_path,
        research={
            "numbers.json": {
                "area": "numbers",
                "entries": [_entry("n-1", sources=[{"url": "https://example.com/a", "tier": 1}])],
                "gaps": [],
            }
        },
        merges=None,
    )
    assert reconcile.main() == 0
    out = json.loads((reconcile.ENTRIES / "numbers.json").read_text())
    assert out["entries"][0].get("exclude") is None


def test_merge_reports_unknown_ids_without_crashing(tmp_path: Path, capsys) -> None:
    _setup(
        tmp_path,
        research={
            "numbers.json": {
                "area": "numbers",
                "entries": [_entry("keep-1", sources=[{"url": "https://a.example/1", "tier": 1}])],
                "gaps": [],
            }
        },
        merges={"merges": [{"keep": "keep-1", "drop": ["does-not-exist"], "reason": "same event"}]},
    )
    assert reconcile.main() == 0
    err = capsys.readouterr().err
    assert "does-not-exist" in err
