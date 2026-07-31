"""Compatibility command routing to the production Digital Sansad roster pipelines."""

from __future__ import annotations

def run(house: str = "ls", cycle: str = "18") -> None:
    normalized_house = house.lower()
    if normalized_house == "ls":
        if cycle != "18":
            raise ValueError("the Digital Sansad LS adapter currently supports cycle 18")
        from neta_ingest.pipelines.lok_sabha import ls_roster

        ls_roster.run()
        return
    if normalized_house == "rs":
        if cycle not in {"current", "RS-CURRENT"}:
            raise ValueError("the Digital Sansad RS adapter currently supports cycle 'current'")
        from neta_ingest.pipelines.rajya_sabha import rajya_sabha

        rajya_sabha.run()
        return
    raise ValueError(f"house must be 'ls' or 'rs', got {house!r}")
