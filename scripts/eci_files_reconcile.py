"""Build data/eci_files/entries/ (what `neta eci-files` loads) from the research files.

For each area, the fact-checked `<area>.verified.json` wins over the raw `<area>.json`. An entry a checker
confirmed or corrected is `checked`; one it could not confirm, or that no checker reached, is `unchecked`;
one it found `wrong` is excluded. An id seen twice keeps the first, checked copies first. Re-run after any
research file changes; review the diff before committing.

If `data/eci_files/merges.json` exists (redesign spec 1d: `{"merges": [{"keep", "drop": [...], "reason"}]}`),
it is applied to the freshly-built entries before they're written: each dropped id is marked `exclude: true`
and its citations are appended to the kept entry's `sources`, deduplicated by url. merges.json is a proposal
only, so this step is a no-op when the file is absent.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "data" / "eci_files" / "research"
ENTRIES = ROOT / "data" / "eci_files" / "entries"
MERGES = ROOT / "data" / "eci_files" / "merges.json"


def _area_file(area_json: Path) -> Path:
    verified = area_json.with_name(area_json.stem + ".verified.json")
    return verified if verified.exists() else area_json


def _apply_merges(area_outputs: dict[str, dict], index: dict[str, tuple[str, int]]) -> int:
    """Mutates area_outputs in place; returns the number of drop ids actually merged."""
    if not MERGES.exists():
        return 0
    merges = json.loads(MERGES.read_text()).get("merges", [])
    applied = 0
    for merge in merges:
        keep_id = merge.get("keep")
        if keep_id not in index:
            print(f"reconcile: merge keep id {keep_id!r} not found in built entries; skipped", file=sys.stderr)
            continue
        keep_file, keep_pos = index[keep_id]
        keep_entry = area_outputs[keep_file]["entries"][keep_pos]
        keep_entry.setdefault("sources", [])
        seen_urls = {src.get("url") for src in keep_entry["sources"]}
        for drop_id in merge.get("drop", []):
            if drop_id not in index:
                print(f"reconcile: merge drop id {drop_id!r} not found in built entries; skipped", file=sys.stderr)
                continue
            drop_file, drop_pos = index[drop_id]
            drop_entry = area_outputs[drop_file]["entries"][drop_pos]
            drop_entry["exclude"] = True
            for src in drop_entry.get("sources", []):
                url = src.get("url")
                if url not in seen_urls:
                    keep_entry["sources"].append(src)
                    seen_urls.add(url)
            applied += 1
    return applied


def main() -> int:
    ENTRIES.mkdir(parents=True, exist_ok=True)
    areas = sorted(p for p in RESEARCH.glob("*.json") if not p.stem.endswith(".verified"))
    seen: set[str] = set()
    report = []
    area_outputs: dict[str, dict] = {}
    index: dict[str, tuple[str, int]] = {}

    for area_json in areas:
        source = _area_file(area_json)
        data = json.loads(source.read_text())
        entries = data.get("entries", [])
        entries.sort(key=lambda e: (e.get("verification") or {}).get("verdict") not in ("confirmed", "corrected"))
        out, excluded, dupes = [], 0, 0
        for e in entries:
            verdict = (e.get("verification") or {}).get("verdict")
            if verdict == "wrong" or not e.get("sources"):
                excluded += 1
                continue
            if e["id"] in seen:
                dupes += 1
                continue
            seen.add(e["id"])
            e["check"] = "checked" if verdict in ("confirmed", "corrected") else "unchecked"
            out.append(e)
        out.sort(key=lambda e: (e.get("date") or "9999", e["id"]))
        area_outputs[area_json.name] = {
            "area": data.get("area", area_json.stem), "entries": out, "gaps": data.get("gaps", [])
        }
        for position, e in enumerate(out):
            index[e["id"]] = (area_json.name, position)
        checked = sum(1 for e in out if e["check"] == "checked")
        report.append(f"{area_json.stem:24} from {source.name:32} {len(out):4} kept "
                      f"({checked} checked)  {excluded} excluded  {dupes} duplicate ids")

    merges_applied = _apply_merges(area_outputs, index)

    for filename, payload in area_outputs.items():
        (ENTRIES / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    print("\n".join(report))
    if MERGES.exists():
        print(f"reconcile: applied {merges_applied} merge(s) from {MERGES.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
