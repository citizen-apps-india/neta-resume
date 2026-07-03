"""Unit tests for merge_cycles._resolve_survivors (pure Python union-find; no DB)."""

from __future__ import annotations

from neta_ingest.pipelines.identity.merge_cycles import _resolve_survivors


def test_simple_pair():
    assert _resolve_survivors([(1, 2)]) == {1: 2}


def test_chain_all_pairs_edges():
    # a 3-cycle same-seat person emits all pairwise edges 1->2, 1->3, 2->3
    assert _resolve_survivors([(1, 2), (1, 3), (2, 3)]) == {1: 3, 2: 3}


def test_name_bridged_chain_without_direct_edge():
    # 1->2 (via seat A), 2->3 (via seat B), no direct 1->3 — still collapses to the terminal
    assert _resolve_survivors([(1, 2), (2, 3)]) == {1: 3, 2: 3}


def test_diamond():
    assert _resolve_survivors([(1, 2), (1, 3), (2, 4), (3, 4)]) == {1: 4, 2: 4, 3: 4}


def test_branch_two_terminals_is_deterministic():
    # one person continuing into two distinct later persons -> pick max() deterministically
    remap = _resolve_survivors([(1, 2), (1, 3)])
    assert remap == {1: 3}
    # survivors (terminals) are never remapped
    assert 2 not in remap and 3 not in remap


def test_disjoint_components():
    assert _resolve_survivors([(1, 2), (10, 11), (11, 12)]) == {1: 2, 10: 12, 11: 12}


def test_empty():
    assert _resolve_survivors([]) == {}


def test_pure_cycle_is_skipped_not_crash():
    # Two same-named different people with crossed seats form a 2-cycle reaching no terminal —
    # ambiguous, so neither is merged (and max([]) must not crash).
    assert _resolve_survivors([(1, 2), (2, 1)]) == {}


def test_cycle_with_an_exit_resolves_to_the_terminal():
    # A cycle 1<->2 that also reaches a real terminal 3 still collapses onto 3.
    assert _resolve_survivors([(1, 2), (2, 1), (2, 3)]) == {1: 3, 2: 3}
