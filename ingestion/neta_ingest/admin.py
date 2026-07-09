"""Schema migrations + reference seeds — the SQL-first, version-tracked runner.

`neta migrate` applies pending `db/migrations/*.sql` (lexical order), each in its own transaction, and
records it in a `schema_migrations` table; `neta seed` (re-)applies the idempotent `db/seeds/*.sql`. This is
the independent path to schema/reference data: CI's migrate workflow runs it against Neon on merge, so the
laptop full-replace is no longer how schema reaches production.

Files are applied with `psql` (robust for multi-statement DDL — the same tool every other doc/script uses;
preinstalled on CI runners). DDL needs owner privileges, so migrate uses `NETA_MIGRATE_DATABASE_URL` when
set, else `NETA_DATABASE_URL`.

Adoption on an already-populated DB: run `neta migrate --baseline` ONCE — it records every existing file as
applied WITHOUT executing it (several early migrations use non-re-runnable ALTERs). After that, plain
`neta migrate` only runs genuinely new files.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from neta_core.config import settings

# Seeds carry FKs (houses/parties before facts), so apply in dependency order — not lexical.
_SEED_ORDER = [
    "houses.sql", "sources.sql", "parties.sql",
    "ipc_bns_sections.sql", "severity_rules.sql", "elections.sql",
    "ministry_themes.sql",
]


def _strip_driver(dsn: str) -> str:
    """psql-compatible DSN: drop the SQLAlchemy +psycopg(2) driver tag."""
    return dsn.replace("+psycopg2", "").replace("+psycopg", "")


def _libpq_dsn(owner: bool) -> str:
    dsn = (settings.migrate_database_url or settings.database_url) if owner else settings.database_url
    return _strip_driver(dsn)


def _pending(names: list[str], applied: set[str]) -> list[str]:
    """Migration filenames not yet recorded, in their given (lexical) order."""
    return [n for n in names if n not in applied]


def _order_seeds(on_disk: set[str]) -> list[str]:
    """Known seeds in FK-dependency order, then any extras alphabetically."""
    return [f for f in _SEED_ORDER if f in on_disk] + sorted(on_disk - set(_SEED_ORDER))


def _psql(dsn: str, *args: str) -> str:
    if not shutil.which("psql"):
        raise RuntimeError("psql not found on PATH (needed for migrate/seed); install postgresql-client")
    res = subprocess.run(  # noqa: S603
        ["psql", dsn, "-v", "ON_ERROR_STOP=1", "-X", "-q", *args],
        capture_output=True, text=True,
    )
    if res.returncode != 0:
        raise RuntimeError(f"psql failed ({res.returncode}): {(res.stderr or res.stdout).strip()}")
    return res.stdout


def _resolve_dir(rel: str) -> Path:
    """Find `rel` (e.g. db/migrations) relative to cwd, else by walking up to the repo root."""
    here = Path(rel)
    if here.is_dir():
        return here
    for parent in [Path.cwd(), *Path.cwd().parents]:
        cand = parent / rel
        if cand.is_dir():
            return cand
    raise FileNotFoundError(f"could not locate '{rel}' from {Path.cwd()}")


def run_migrate(dir: str = "db/migrations", baseline: bool = False) -> None:
    mig_dir = _resolve_dir(dir)
    files = sorted(mig_dir.glob("*.sql"))
    dsn = _libpq_dsn(owner=True)

    _psql(dsn, "-c", "CREATE TABLE IF NOT EXISTS schema_migrations "
                     "(version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())")
    applied = {v for v in _psql(dsn, "-tAc", "SELECT version FROM schema_migrations").split() if v}
    by_name = {p.name: p for p in files}
    pending = [by_name[n] for n in _pending([p.name for p in files], applied)]

    if not pending:
        print(f"[migrate] up to date ({len(applied)} applied, {len(files)} on disk)")
        return
    if baseline:
        for p in pending:
            _psql(dsn, "-c", f"INSERT INTO schema_migrations (version) VALUES ('{p.name}') "
                             "ON CONFLICT DO NOTHING")
            print(f"   = baselined {p.name}")
        print(f"[migrate] baselined {len(pending)} migration(s) as applied (not executed)")
        return

    for p in pending:
        # -1 wraps the file + its version record in ONE transaction: a failed file records nothing.
        _psql(dsn, "-1", "-f", str(p),
              "-c", f"INSERT INTO schema_migrations (version) VALUES ('{p.name}')")
        print(f"   + applied {p.name}")
    print(f"[migrate] applied {len(pending)} migration(s); {len(applied) + len(pending)} total")


def run_seed(dir: str = "db/seeds") -> None:
    seed_dir = _resolve_dir(dir)
    ordered = _order_seeds({p.name for p in seed_dir.glob("*.sql")})
    dsn = _libpq_dsn(owner=True)
    for name in ordered:
        _psql(dsn, "-1", "-f", str(seed_dir / name))  # seeds are idempotent (ON CONFLICT / IF NOT EXISTS)
        print(f"   ~ seeded {name}")
    print(f"[seed] applied {len(ordered)} seed file(s)")
    run_seed_states()


def run_seed_states() -> None:
    """Upsert state/UT assembly house + term_cycle rows from the elections registry (idempotent)."""
    from neta_sources.myneta import elections

    dsn = _libpq_dsn(owner=True)
    for a in elections.ASSEMBLIES:
        name = a.name.replace("'", "''")
        _psql(dsn, "-c",
              f"INSERT INTO house (code, name, jurisdiction, state_code) "
              f"VALUES ('{a.house_code}', '{name}', 'state', '{a.state_code}') ON CONFLICT (code) DO NOTHING")
        for c in a.cycles:
            end = f"DATE '{c.term_end}'" if c.term_end else "NULL"
            _psql(dsn, "-c",
                  f"INSERT INTO term_cycle (house_id, number, start_date, end_date, eci_election_id) "
                  f"SELECT h.id, {c.number}, DATE '{c.poll_date}', {end}, '{c.eci_id}' "
                  f"FROM house h WHERE h.code = '{a.house_code}' ON CONFLICT (house_id, number) DO NOTHING")
        print(f"   ~ seeded assembly {a.house_code} ({len(a.cycles)} cycle(s))")
    print(f"[seed-states] {len(elections.ASSEMBLIES)} assembly(ies) from the registry")
