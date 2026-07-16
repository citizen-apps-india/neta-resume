"""India Dashboard — public-institution counts (schools, hospitals, colleges, courts, police, …).

Two provenance modes, same fact table (macro_indicator_value) and the same catalog (macro_indicator_def,
seeded from db/seeds/institution_indicators.sql):

  1. CURATED — headline national figures transcribed from official ministry/agency reports (UDISE+, AISHE,
     Health Dynamics of India, NCRB, BPR&D, India Post, RBI, Indian Railways). Each value records a
     source_ref pointing at that report's official URL (raw_name = the report + vintage). These are
     tier-1 facts, hand-verified, with the citation one click away — "no fact without a source".

  2. OGD — the subset data.gov.in exposes as clean resources refreshes automatically via the OGD resource
     API (needs NETA_DATAGOVIN_API_KEY). When a key is present, an OGD value overrides the curated one for
     that code; when it is absent, the OGD path no-ops with a log line and the curated figure stands.

Idempotent — source_ref upserts on (source, native_id) and values upsert on
(indicator_code, country_code, year). Missing ≠ zero.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text

from neta_core.db.engine import session_scope
from neta_core.provenance import record_source_ref
from neta_sources.datagovin import client as ogd

_UPSERT = text("""
    INSERT INTO macro_indicator_value (indicator_code, country_code, year, value, source_ref_id, fetched_at)
    VALUES (:code, 'IND', :year, :value, :sr, now())
    ON CONFLICT (indicator_code, country_code, year)
    DO UPDATE SET value = EXCLUDED.value, source_ref_id = EXCLUDED.source_ref_id,
                  fetched_at = EXCLUDED.fetched_at
""")


@dataclass(slots=True)
class Curated:
    code: str
    year: int
    value: float
    source_code: str
    native_url: str
    report: str            # the report + vintage the figure was transcribed from (-> source_ref.raw_name)


# Verified national counts, each transcribed from the named official release. Where two years are given the
# tile can show a trend + a year-on-year change; a single year renders as a big number + "as of".
_CURATED: list[Curated] = [
    # Education — UDISE+ 2023-24 (school education) + AISHE 2023-24 (higher education), Ministry of Education
    Curated("IN.EDU.SCHOOLS",      2023, 1_472_000,   "moe_udise", "https://udiseplus.gov.in/",  "UDISE+ 2023-24"),
    Curated("IN.EDU.TEACHERS",     2023, 9_800_000,   "moe_udise", "https://udiseplus.gov.in/",  "UDISE+ 2023-24"),
    Curated("IN.EDU.STUDENTS",     2023, 248_000_000, "moe_udise", "https://udiseplus.gov.in/",  "UDISE+ 2023-24"),
    Curated("IN.EDU.UNIVERSITIES", 2023, 1_289,       "moe_aishe", "https://aishe.gov.in/",      "AISHE 2023-24"),
    Curated("IN.EDU.COLLEGES",     2023, 48_246,      "moe_aishe", "https://aishe.gov.in/",      "AISHE 2023-24"),
    Curated("IN.EDU.STANDALONE",   2023, 15_221,      "moe_aishe", "https://aishe.gov.in/",      "AISHE 2023-24"),
    Curated("IN.EDU.HE.ENROLMENT", 2022, 44_600_000,  "moe_aishe", "https://aishe.gov.in/",      "AISHE 2022-23"),
    Curated("IN.EDU.HE.ENROLMENT", 2023, 45_000_000,  "moe_aishe", "https://aishe.gov.in/",      "AISHE 2023-24"),
    Curated("IN.EDU.HE.FACULTY",   2023, 1_732_000,   "moe_aishe", "https://aishe.gov.in/",      "AISHE 2023-24"),
    # Health — Health Dynamics of India (Infrastructure & HR) 2022-23, MoHFW (formerly Rural Health Statistics)
    Curated("IN.HLTH.SUBCENTRES",    2022, 169_615, "mohfw_hdi", "https://mohfw.gov.in/", "Health Dynamics of India 2022-23"),
    Curated("IN.HLTH.PHC",           2022, 31_882,  "mohfw_hdi", "https://mohfw.gov.in/", "Health Dynamics of India 2022-23"),
    Curated("IN.HLTH.CHC",           2022, 6_359,   "mohfw_hdi", "https://mohfw.gov.in/", "Health Dynamics of India 2022-23"),
    Curated("IN.HLTH.SDH",           2022, 1_340,   "mohfw_hdi", "https://mohfw.gov.in/", "Health Dynamics of India 2022-23"),
    Curated("IN.HLTH.DISTRICT.HOSP", 2022, 714,     "mohfw_hdi", "https://mohfw.gov.in/", "Health Dynamics of India 2022-23"),
    # Justice & Safety — BPR&D Data on Police Organisations (1 Jan 2024) + NCRB Prison Statistics India 2022
    Curated("IN.JUS.POLICE.SANCTIONED", 2024, 2_755_000, "bprd", "https://bprd.nic.in/page/dopo", "BPR&D DoPO 2024"),
    Curated("IN.JUS.POLICE.ACTUAL",     2024, 2_162_000, "bprd", "https://bprd.nic.in/page/dopo", "BPR&D DoPO 2024"),
    Curated("IN.JUS.PRISON.POP",        2022, 573_220,   "ncrb", "https://www.ncrb.gov.in/en/prison-statistics-india", "NCRB Prison Statistics India 2022"),
    Curated("IN.JUS.PRISON.CAPACITY",   2022, 436_266,   "ncrb", "https://www.ncrb.gov.in/en/prison-statistics-india", "NCRB Prison Statistics India 2022"),
    Curated("IN.JUS.PRISON.OCCUPANCY",  2022, 131,       "ncrb", "https://www.ncrb.gov.in/en/prison-statistics-india", "NCRB Prison Statistics India 2022"),
    # Connectivity & Utilities — India Post, RBI, Indian Railways
    Curated("IN.CONN.POSTOFFICES",   2024, 164_999, "indiapost",  "https://www.indiapost.gov.in/", "India Post network"),
    Curated("IN.CONN.BANK.BRANCHES", 2024, 165_501, "rbi",        "https://www.rbi.org.in/",       "RBI, Sep 2024"),
    Curated("IN.CONN.RAIL.STATIONS", 2023, 7_325,   "indianrail", "https://indianrailways.gov.in/", "Indian Railways 2023-24"),
]

# OGD auto-refresh registry: indicator code -> (resource_id, record-field, year). When
# NETA_DATAGOVIN_API_KEY is set, each entry's rows are fetched and summed to a national total that
# overrides the curated figure. Empty until a resource UUID is wired (see docs); the mechanism below is
# exercised by the no-op path meanwhile.
#   e.g. "IN.CONN.BANK.BRANCHES": ("<resource-uuid>", "no_of_offices", 2024)
_OGD_RESOURCES: dict[str, tuple[str, str, int]] = {}


def _write(entries: list[tuple[Curated | None, str, int, float, str, str, str]]) -> tuple[int, set[str]]:
    """Persist (source_ref + value) rows; return (count, distinct codes touched)."""
    codes: set[str] = set()
    with session_scope() as s:
        for _, code, year, value, source_code, native_url, report in entries:
            sr = record_source_ref(
                s, source_code=source_code, native_id=f"{code}-{year}",
                native_url=native_url, raw_name=report,
            )
            s.execute(_UPSERT, {"code": code, "year": year, "value": value, "sr": sr})
            codes.add(code)
    return len(entries), codes


def run(only: list[str] | None = None) -> None:
    wanted = set(only) if only else None

    # 1. Curated figures — the tier-1 baseline that always lands.
    curated = [c for c in _CURATED if wanted is None or c.code in wanted]
    n, codes = _write([(c, c.code, c.year, c.value, c.source_code, c.native_url, c.report) for c in curated])
    print(f"[institution-stats] curated: {n} value(s) across {len(codes)} indicator(s)")

    # 2. OGD refresh — override the subset data.gov.in serves, when a key is configured.
    resources = {k: v for k, v in _OGD_RESOURCES.items() if wanted is None or k in wanted}
    if not resources:
        print("[institution-stats] OGD: no resources registered — curated figures stand")
    elif not ogd.have_api_key():
        print(f"[institution-stats] OGD: skipped {len(resources)} resource(s) — set NETA_DATAGOVIN_API_KEY "
              "to auto-refresh; curated figures stand")
    else:
        for code, (resource_id, field, year) in resources.items():
            try:
                page = ogd.fetch_resource(resource_id)
                total = sum(float(r[field]) for r in page.records if r.get(field) not in (None, ""))
                _write([(None, code, year, total, "datagovin", page.native_url, f"data.gov.in {resource_id}")])
                print(f"  + OGD {code}: {total:,.0f} from {len(page.records)} rows ({year})")
            except Exception as e:  # a bad resource/field must not abort — curated figure stands
                print(f"  ! OGD {code}: {e!r} — curated figure stands")

    print("[institution-stats] done")
