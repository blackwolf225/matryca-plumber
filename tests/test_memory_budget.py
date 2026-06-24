"""Tests for RAM budget hooks and Phase 1 teardown."""

from __future__ import annotations

from pathlib import Path

import pytest
from src.agent.memory_budget import release_phase1_memory, snapshot
from src.graph.generational_cache import get_cached_bm25_corpus, release_bm25_corpus
from src.graph.master_catalog import load_master_catalog, unload_master_catalog


def test_release_phase1_memory_clears_bm25_cache(tmp_path: Path) -> None:
    pages = tmp_path / "pages"
    pages.mkdir(parents=True)
    (pages / "A.md").write_text("- alpha beta gamma\n", encoding="utf-8")
    corpus = get_cached_bm25_corpus(tmp_path)
    assert corpus.n_docs >= 1
    release_phase1_memory(tmp_path)
    release_bm25_corpus(tmp_path)
    from src.graph.generational_cache import _bm25_cache

    assert str(tmp_path.resolve()) not in _bm25_cache


def test_unload_master_catalog(tmp_path: Path) -> None:
    pages = tmp_path / "pages"
    pages.mkdir(parents=True)
    (pages / "A.md").write_text("- x\n", encoding="utf-8")
    load_master_catalog(tmp_path)
    assert unload_master_catalog(tmp_path) is True
    assert unload_master_catalog(tmp_path) is False


def test_memory_snapshot_returns_positive_rss() -> None:
    snap = snapshot()
    assert snap.rss_bytes > 0
    assert snap.budget_mb >= 512


def test_generational_cache_lru_evicts_oldest_alias_graph(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.graph.generational_cache as gc_module
    from src.graph.generational_cache import (
        _alias_cache,
        cached_build_alias_index,
        clear_generational_caches,
    )

    clear_generational_caches()
    monkeypatch.setattr(gc_module, "_generational_cache_max_graphs", lambda: 2)
    roots = [tmp_path / f"g{i}" for i in range(3)]
    for root in roots:
        pages = root / "pages"
        pages.mkdir(parents=True)
        (pages / "A.md").write_text("- alpha\n", encoding="utf-8")
        cached_build_alias_index(root)
    assert len(_alias_cache) == 2
    assert str(roots[0].resolve()) not in _alias_cache
    assert str(roots[2].resolve()) in _alias_cache


def test_generational_cache_lru_evicts_oldest_bm25_graph(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.graph.generational_cache as gc_module
    from src.graph.generational_cache import (
        _bm25_cache,
        clear_generational_caches,
        get_cached_bm25_corpus,
    )

    clear_generational_caches()
    monkeypatch.setenv("MATRYCA_BM25_MODE", "resident")
    monkeypatch.setattr(gc_module, "_generational_cache_max_graphs", lambda: 2)
    roots = [tmp_path / f"g{i}" for i in range(3)]
    for root in roots:
        pages = root / "pages"
        pages.mkdir(parents=True)
        (pages / "A.md").write_text("- alpha beta\n", encoding="utf-8")
        get_cached_bm25_corpus(root)
    assert len(_bm25_cache) == 2
    assert str(roots[0].resolve()) not in _bm25_cache
    assert str(roots[2].resolve()) in _bm25_cache
