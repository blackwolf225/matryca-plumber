"""Slow performance regression tests for semantic clustering (excluded from make test-fast)."""

from __future__ import annotations

import time

import pytest
from src.graph.semantic_clustering import (
    DEFAULT_MAX_CLUSTER_SIZE,
    MIN_CLUSTER_SIZE,
    compute_semantic_clusters,
)
from tests.test_semantic_clustering import _mock_catalog

# Under full-suite CPU load, Louvain on 3000 pages can exceed 8s on a loaded laptop.
# Isolated runs typically finish in 1.5–3.5s; 15s catches major algorithmic regressions.
_SCALE_CEILING_SECONDS = 15.0


@pytest.mark.slow
def test_compute_semantic_clusters_scales_to_three_thousand_pages() -> None:
    catalog = _mock_catalog(3000)
    started = time.perf_counter()
    clusters = compute_semantic_clusters(catalog, max_cluster_size=DEFAULT_MAX_CLUSTER_SIZE)
    elapsed = time.perf_counter() - started

    titles = [title for page_titles in clusters.values() for title in page_titles]
    sizes = [len(page_titles) for page_titles in clusters.values()]

    assert len(titles) == 3000
    assert len(set(titles)) == 3000
    assert all(MIN_CLUSTER_SIZE <= size <= DEFAULT_MAX_CLUSTER_SIZE for size in sizes)
    assert elapsed < _SCALE_CEILING_SECONDS, (
        f"clustering took {elapsed:.3f}s, expected under {_SCALE_CEILING_SECONDS}s"
    )
