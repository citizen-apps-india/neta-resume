"""Unit tests for the pure transform logic (no DB needed): money, sections, names."""

from neta_ingest.transform.money import parse_rupees
from neta_ingest.transform.names import normalize_name
from neta_ingest.transform.sections import parse_sections, rollup_severity


class TestParseRupees:
    def test_indian_grouping(self):
        assert parse_rupees("Rs 1,23,45,678") == 12345678

    def test_crore_word(self):
        assert parse_rupees("5 Crore+") == 50000000
        assert parse_rupees("1.5 crore") == 15000000

    def test_lakh_word(self):
        assert parse_rupees("2.5 Lakh") == 250000

    def test_strips_human_gloss(self):
        # MyNeta appends "~ 2.5 Lakh"; the precise figure must win.
        assert parse_rupees("Rs 2,50,000 ~ 2.5 Lakh+") == 250000

    def test_nil_and_empty(self):
        for v in ("Nil", "", "-", "N/A", None):
            assert parse_rupees(v) == 0


class TestParseSections:
    def test_simple_ipc(self):
        assert parse_sections("IPC 302") == [("IPC", "302")]

    def test_multiple_with_slash(self):
        assert parse_sections("u/s 302/34 IPC") == [("IPC", "302"), ("IPC", "34")]

    def test_bns(self):
        assert parse_sections("BNS 103") == [("BNS", "103")]

    def test_default_code_when_absent(self):
        assert parse_sections("420", default_code="IPC") == [("IPC", "420")]


class TestRollupSeverity:
    def test_max_wins(self):
        assert rollup_severity(["minor", "heinous", "serious"]) == "heinous"
        assert rollup_severity(["minor", "serious"]) == "serious"

    def test_none_when_unclassified(self):
        assert rollup_severity([None, None]) is None


class TestNormalizeName:
    def test_strips_honorific_and_sorts(self):
        assert normalize_name("Dr. Shashi Tharoor") == "shashi tharoor"

    def test_token_sort_collides_order_variants(self):
        assert normalize_name("Narendra Modi") == normalize_name("Modi Narendra")
