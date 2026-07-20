"""Attach 18th-Lok-Sabha parliamentary committee memberships to sitting MPs (the `role` table).

Source: the sansad.in committee API (official, trust_tier 1). For each committee we fetch its roster,
match every member to the EXISTING person by name (the API carries no mpsno), and write a
`role(role_type='committee_member' | 'committee_chair', body=<committee name>, house_id=LS)`. The
schema + profile UI already render these role types (they were defined for exactly this, but nothing
populated them until now).

Idempotent: each committee owns one source_ref (native_id 'ls-committee-{loksabha}-{code}') whose raw
member list is snapshotted to the raw_cache; a re-run deletes that source_ref's roles and reinserts, so
committee reshuffles are picked up cleanly. Members not uniquely matched to a person are skipped (precision
over recall — never attach the wrong person's role), the same discipline as the leadership pipeline.
"""

from __future__ import annotations

import json
from dataclasses import asdict

from sqlalchemy import text

from neta_core.db.engine import session_scope
from neta_core.provenance import cache_raw, record_source_ref
from neta_core.transform.names import normalize_name
from neta_ingest.pipelines.identity.affidavit_attach import name_tokens
from neta_sources.sansad import committees as sansad_committees

# 18th Lok Sabha term start — the idempotency-key fallback when a committee has no formation date.
_TERM_START = "2024-06-24"


def _match_person(persons: list, name: str) -> int | None:
    """Unique person for a name: token-superset (handles middle names/honorifics), then exact
    normalized-name equality (handles initials). Ambiguous or absent -> None (skip, don't guess)."""
    want = name_tokens(name)
    hits = [p.id for p in persons if want and want <= name_tokens(p.display_name)]
    if len(hits) == 1:
        return hits[0]
    key = normalize_name(name)
    exact = [p.id for p in persons if normalize_name(p.display_name) == key]
    return exact[0] if len(exact) == 1 else None


def run(loksabha: int = 18, limit: int | None = None) -> None:
    """Ingest committee memberships for `loksabha`. `limit` caps the number of committees fetched (testing)."""
    committees = sansad_committees.fetch_committees(loksabha)
    if limit is not None:
        committees = committees[:limit]
    print(f"[committees] {len(committees)} committees from sansad (LS {loksabha}) …")

    committees_done = attached = chairs = missing = 0
    with session_scope() as s:
        persons = s.execute(text("SELECT id, display_name FROM person")).all()
        ls_house_id = s.execute(text("SELECT id FROM house WHERE code = 'LS'")).scalar()
        for c in committees:
            members = sansad_committees.fetch_committee_members(c.code, loksabha)
            if not members:
                continue
            # One source_ref per committee; snapshot its raw roster as the provenance archive.
            raw = json.dumps([asdict(m) for m in members], ensure_ascii=False).encode("utf-8")
            payload_ref = cache_raw(raw, suffix=".json")
            sref = record_source_ref(
                s, source_code="sansad",
                native_id=f"ls-committee-{loksabha}-{c.code}",
                native_url="https://sansad.in/ls/committee",
                raw_name=c.name, raw_payload_ref=payload_ref,
            )
            # Idempotent: clear this committee's previously-written roles, then reinsert the current roster.
            s.execute(text("DELETE FROM role WHERE source_ref_id = :sr"), {"sr": sref})
            for m in members:
                pid = _match_person(persons, m.member_name)
                if pid is None:
                    missing += 1
                    continue
                role_type = "committee_chair" if m.is_chairperson else "committee_member"
                lead = "Chairperson" if m.is_chairperson else "Member"
                s.execute(
                    text(
                        """
                        INSERT INTO role
                          (person_id, role_type, title, body, house_id, start_date, status, source_ref_id)
                        VALUES (:pid, :rt, :title, :body, :hid, :start, 'current', :sr)
                        ON CONFLICT (person_id, role_type, body, start_date) DO UPDATE
                          SET title = EXCLUDED.title, house_id = EXCLUDED.house_id,
                              source_ref_id = EXCLUDED.source_ref_id
                        """
                    ),
                    {"pid": pid, "rt": role_type, "title": f"{lead}, {c.name}", "body": c.name,
                     "hid": ls_house_id, "start": m.formation_date or _TERM_START, "sr": sref},
                )
                attached += 1
                chairs += 1 if m.is_chairperson else 0
            committees_done += 1
    print(f"[committees] {committees_done} committees, {attached} memberships "
          f"({chairs} chairs), {missing} members unmatched.")
