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
        Cycle("TN_VS2006", 2006, "2006-05-13", "2011-05-12", "https://www.myneta.info/TN2006"),  # legacy slug
    )),
    # Batch 1 — the largest remaining states (URLs verified live; 2013-era gaps omitted, not faked).
    Assembly("MP_VS", "Madhya Pradesh Vidhan Sabha", "MP", (
        Cycle("MP_VS2023", 2023, "2023-12-03", None,         "https://www.myneta.info/MadhyaPradesh2023"),
        Cycle("MP_VS2018", 2018, "2018-12-11", "2023-12-02", "https://www.myneta.info/MadhyaPradesh2018"),
        Cycle("MP_VS2013", 2013, "2013-12-08", "2018-12-10", "https://www.myneta.info/MP2013"),  # legacy slug
    )),
    Assembly("WB_VS", "West Bengal Legislative Assembly", "WB", (
        Cycle("WB_VS2026", 2026, "2026-05-02", None,         "https://www.myneta.info/WestBengal2026"),  # est. date
        Cycle("WB_VS2021", 2021, "2021-05-02", "2026-05-01", "https://www.myneta.info/WestBengal2021"),
        Cycle("WB_VS2016", 2016, "2016-05-19", "2021-05-01", "https://www.myneta.info/WestBengal2016"),
        Cycle("WB_VS2011", 2011, "2011-05-13", "2016-05-18", "https://www.myneta.info/WestBengal2011"),
        Cycle("WB_VS2006", 2006, "2006-05-11", "2011-05-12", "https://www.myneta.info/WB2006"),  # legacy slug
    )),
    Assembly("BR_VS", "Bihar Vidhan Sabha", "BR", (
        Cycle("BR_VS2025", 2025, "2025-11-14", None,         "https://www.myneta.info/Bihar2025"),  # est. date
        Cycle("BR_VS2020", 2020, "2020-11-10", "2025-11-13", "https://www.myneta.info/Bihar2020"),
        Cycle("BR_VS2015", 2015, "2015-11-08", "2020-11-09", "https://www.myneta.info/Bihar2015"),
    )),
    Assembly("KA_VS", "Karnataka Legislative Assembly", "KA", (
        Cycle("KA_VS2023", 2023, "2023-05-13", None,         "https://www.myneta.info/Karnataka2023"),
        Cycle("KA_VS2018", 2018, "2018-05-15", "2023-05-12", "https://www.myneta.info/Karnataka2018"),
        Cycle("KA_VS2013", 2013, "2013-05-08", "2018-05-14", "https://www.myneta.info/Karnataka2013"),
    )),
    Assembly("RJ_VS", "Rajasthan Vidhan Sabha", "RJ", (
        Cycle("RJ_VS2023", 2023, "2023-12-03", None,         "https://www.myneta.info/Rajasthan2023"),
        Cycle("RJ_VS2018", 2018, "2018-12-11", "2023-12-02", "https://www.myneta.info/Rajasthan2018"),
        Cycle("RJ_VS2013", 2013, "2013-12-08", "2018-12-10", "https://www.myneta.info/Rajasthan2013"),
        Cycle("RJ_VS2008", 2008, "2008-12-08", "2013-12-07", "https://www.myneta.info/RJ2008"),  # legacy slug
    )),
    Assembly("GJ_VS", "Gujarat Vidhan Sabha", "GJ", (
        Cycle("GJ_VS2022", 2022, "2022-12-08", None,         "https://www.myneta.info/Gujarat2022"),
        Cycle("GJ_VS2017", 2017, "2017-12-18", "2022-12-07", "https://www.myneta.info/Gujarat2017"),
        Cycle("GJ_VS2012", 2012, "2012-12-20", "2017-12-17", "https://www.myneta.info/Gujarat2012"),
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
