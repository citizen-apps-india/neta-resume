"""Unit tests for the migration/seed runner's pure logic (no DB)."""

from __future__ import annotations

from neta_ingest.admin import _order_seeds, _pending, _strip_driver


def test_strip_driver():
    assert _strip_driver("postgresql+psycopg://u:p@h/d") == "postgresql://u:p@h/d"
    assert _strip_driver("postgresql+psycopg2://u:p@h/d") == "postgresql://u:p@h/d"
    assert _strip_driver("postgresql://u:p@h/d") == "postgresql://u:p@h/d"


def test_pending_is_ordered_set_difference():
    names = ["0001_a.sql", "0002_b.sql", "0003_c.sql"]
    assert _pending(names, set()) == names
    assert _pending(names, {"0001_a.sql", "0002_b.sql"}) == ["0003_c.sql"]
    assert _pending(names, set(names)) == []
    # order preserved even if applied set is unordered
    assert _pending(names, {"0002_b.sql"}) == ["0001_a.sql", "0003_c.sql"]


def test_order_seeds_dependency_order_then_extras():
    on_disk = {"parties.sql", "houses.sql", "sources.sql", "zzz_extra.sql"}
    ordered = _order_seeds(on_disk)
    # houses before parties (FK order); unknown extras appended alphabetically last
    assert ordered.index("houses.sql") < ordered.index("parties.sql")
    assert ordered[-1] == "zzz_extra.sql"
    # missing known seeds are simply skipped (no KeyError)
    assert _order_seeds({"houses.sql"}) == ["houses.sql"]
