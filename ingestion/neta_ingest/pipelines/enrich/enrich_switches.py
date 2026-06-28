"""Attach sourced 'why' narratives to detected party-switch events (the reported-reason layer).

Switch EVENTS are detected structurally (party differs across cycles). The reason a person switched
has no structured source, so it is curated here from public reporting — quoted, dated, and cited,
never inferred. Each narrative is tagged with a news/encyclopaedia source (trust tier 3, "reported")
and the UI labels it as reported. Keyed by name so it survives re-ingestion.
"""

from __future__ import annotations

from sqlalchemy import text

from neta_core.db.engine import session_scope

# name prefix -> (narrative, ISO date, source url, publication)
SWITCHES = [
    (
        "BHARTRUHARI MAHTAB",
        "Resigned from the BJD on 22 March 2024 with a “broken heart,” saying he had for about "
        "two-and-a-half years been prevented from raising his voice on party matters; joined the BJP "
        "on 28 March 2024.",
        "2024-03-28",
        "https://www.thehansindia.com/news/national/senior-parliamentarian-bhartruhari-mahtab-resigns-from-bjd-with-broken-heart-867052",
        "The Hans India",
    ),
    (
        "RAHUL KASWAN",
        "Resigned from the BJP and joined the Congress on 11 March 2024 after being denied a Lok Sabha "
        "ticket (the BJP fielded Devendra Jhajharia in Churu); said the BJP “does not want strong "
        "leaders to grow.”",
        "2024-03-11",
        "https://www.indiatvnews.com/news/india/rahul-kaswan-churu-bjp-mp-congress-rajasthan-denied-ticket-lok-sabha-elections-2024-reactions-latest-updates-2024-03-11-920883",
        "India TV News",
    ),
    (
        "MAGUNTA SREENIVASULU REDDY",
        "Quit the YSRCP on 28 February 2024 and joined the TDP on 16 March 2024, citing “self-respect”; "
        "reporting links the exit to the YSRCP fielding another candidate in Ongole.",
        "2024-03-16",
        "https://en.wikipedia.org/wiki/Magunta_Sreenivasulu_Reddy",
        "Wikipedia",
    ),
    (
        "BALASHOWRY VALLABHANENI",
        "Resigned from the YSRCP on 13 January 2024 to join the Jana Sena Party, reportedly after being "
        "told he would not get a ticket and amid disagreements with MLAs in his constituency.",
        "2024-01-13",
        "https://www.thenewsminute.com/andhra-pradesh/andhra-machilipatnam-mp-quits-ysrcp-second-mp-to-resign-in-less-than-a-week",
        "The News Minute",
    ),
    (
        "OMPRAKASH BHUPALSINH",
        "Reflects the 2022 Shiv Sena split into the Shinde faction (Shiv Sena) and the Uddhav Thackeray "
        "faction, Shiv Sena (UBT). He contested and won the 2024 Dharashiv (Osmanabad) seat as the "
        "Shiv Sena (UBT) candidate.",
        "2024-06-04",
        "https://en.wikipedia.org/wiki/2022_Maharashtra_political_crisis",
        "Wikipedia",
    ),
    (
        "RAVIKUMAR",
        "Not a defection: D. Ravikumar is a VCK leader, and the VCK contests within the DMK-led front. "
        "In 2019 he won on the DMK “rising sun” symbol (the VCK was then unrecognised); in 2024 he won "
        "under the VCK’s own symbol.",
        "2024-06-04",
        "https://en.wikipedia.org/wiki/Viduthalai_Chiruthaigal_Katchi",
        "Wikipedia",
    ),
]


def run() -> None:
    with session_scope() as s:
        news_source_id = s.execute(text("SELECT id FROM source WHERE code = 'news'")).scalar()
        updated = 0
        for name, narrative, date, url, pub in SWITCHES:
            pid = s.execute(
                text("SELECT id FROM person WHERE display_name LIKE :n ORDER BY id LIMIT 1"),
                {"n": f"{name}%"},
            ).scalar()
            if pid is None:
                print(f"[switch] no person matched '{name}' — skipping")
                continue
            source_ref_id = s.execute(
                text(
                    """
                    INSERT INTO source_ref (source_id, native_id, native_url, raw_name, person_id)
                    VALUES (:sid, :nid, :url, :pub, :pid)
                    ON CONFLICT (source_id, native_id) DO UPDATE
                      SET native_url = EXCLUDED.native_url, raw_name = EXCLUDED.raw_name
                    RETURNING id
                    """
                ),
                {"sid": news_source_id, "nid": f"switch-{pid}", "url": url, "pub": pub, "pid": pid},
            ).scalar()
            res = s.execute(
                text(
                    """
                    UPDATE party_switch_event
                    SET narrative = :n, event_date = :d, narrative_source_ref_id = :sr
                    WHERE person_id = :pid
                    """
                ),
                {"n": narrative, "d": date, "sr": source_ref_id, "pid": pid},
            )
            updated += res.rowcount
            print(f"[switch] {name}: {res.rowcount} event(s) enriched")
        print(f"[switch] done: {updated} switch event(s) given a sourced reason")
