"""Build data/eci_files/entries/ (what `neta eci-files` loads) from the research files.

For each area, the fact-checked `<area>.verified.json` wins over the raw `<area>.json`. An entry a checker
confirmed or corrected is `checked`; one it could not confirm, or that no checker reached, is `unchecked`;
one it found `wrong` is excluded. An id seen twice keeps the first, checked copies first. Re-run after any
research file changes; review the diff before committing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "data" / "eci_files" / "research"
ENTRIES = ROOT / "data" / "eci_files" / "entries"


def _area_file(area_json: Path) -> Path:
    verified = area_json.with_name(area_json.stem + ".verified.json")
    return verified if verified.exists() else area_json


def main() -> int:
    ENTRIES.mkdir(parents=True, exist_ok=True)
    areas = sorted(p for p in RESEARCH.glob("*.json") if not p.stem.endswith(".verified"))
    seen: set[str] = set()
    report = []
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
        (ENTRIES / area_json.name).write_text(
            json.dumps({"area": data.get("area", area_json.stem), "entries": out, "gaps": data.get("gaps", [])},
                       ensure_ascii=False, indent=2) + "\n"
        )
        checked = sum(1 for e in out if e["check"] == "checked")
        report.append(f"{area_json.stem:24} from {source.name:32} {len(out):4} kept "
                      f"({checked} checked)  {excluded} excluded  {dupes} duplicate ids")
    print("\n".join(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
