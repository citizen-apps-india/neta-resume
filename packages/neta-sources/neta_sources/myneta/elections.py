"""State/UT assembly election registry — the data that lets the house-generic pipeline onboard a state.

Each assembly lists its house code + name + ISO state_code and the cleanly-available MyNeta cycles
(each URL verified live before entry — MyNeta slugs can't be derived algorithmically). `number` is the
election year (monotonic per house; used only for ordering — never compared across houses). Consumed by:

  - `myneta.client.ELECTION_BASE`  (merges in {eci_id: url}, so base_url() resolves state cycles)
  - `neta seed-states`             (upserts the house + term_cycle rows)
  - `neta onboard-state --house X` (runs the ingest sequence over a house's cycles)

To add a state: probe its `<State><Year>` MyNeta URLs, add an Assembly entry, ship the PR, then dispatch
`onboard-state`. Coverage is the reliable ~2013→2026 window; older/absent cycles are omitted, not faked.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Cycle:
    eci_id: str            # the cycle key used everywhere, e.g. "UP_VS2022"
    number: int            # election year — ordering only
    poll_date: str         # ECI result date (ISO)
    term_end: str | None   # None = current (latest) cycle
    url: str               # MyNeta site root, verified live


@dataclass(frozen=True)
class Assembly:
    house_code: str        # e.g. "UP_VS"
    name: str              # e.g. "Uttar Pradesh Vidhan Sabha"
    state_code: str        # ISO 3166-2:IN, e.g. "UP"
    cycles: tuple[Cycle, ...]


# Pilot set (Part C). Batches append here as states are verified + onboarded.
ASSEMBLIES: tuple[Assembly, ...] = (
    Assembly("UP_VS", "Uttar Pradesh Vidhan Sabha", "UP", (
        Cycle("UP_VS2022", 2022, "2022-03-10", None,         "https://www.myneta.info/UttarPradesh2022"),
        Cycle("UP_VS2017", 2017, "2017-03-11", "2022-03-09", "https://www.myneta.info/UttarPradesh2017"),
    )),
    Assembly("TN_VS", "Tamil Nadu Legislative Assembly", "TN", (
        Cycle("TN_VS2021", 2021, "2021-05-02", None,         "https://www.myneta.info/TamilNadu2021"),
        Cycle("TN_VS2016", 2016, "2016-05-19", "2021-05-01", "https://www.myneta.info/TamilNadu2016"),
        Cycle("TN_VS2011", 2011, "2011-05-13", "2016-05-18", "https://www.myneta.info/TamilNadu2011"),
    )),
)


def election_base() -> dict[str, str]:
    """{eci_id: myneta_url} for every registered state cycle (merged into myneta.ELECTION_BASE)."""
    return {c.eci_id: c.url for a in ASSEMBLIES for c in a.cycles}


def assembly(house_code: str) -> Assembly:
    code = house_code.upper()
    for a in ASSEMBLIES:
        if a.house_code == code:
            return a
    raise KeyError(f"no registered assembly for house {house_code!r}")
