"""Tests for namespace hub index and OCC-protected generated hub writes."""

from __future__ import annotations

from pathlib import Path

import pytest
from src.config import MatrycaWikiConfig
from src.graph.generated_hub_write import write_generated_hub_page
from src.graph.hubs import build_namespace_index_markdown
from src.graph.insights_engine import GRAPH_INSIGHTS_TITLE, write_graph_insights_page
from src.graph.markdown_blocks import occ_snapshot
from src.graph.master_catalog import (
    MASTER_INDEX_PAGE_TITLE,
    CatalogEntry,
    MasterCatalog,
    master_index_page_path,
    write_master_index_page,
)
from src.graph.path_sandbox import graph_safe_page_path


@pytest.fixture
def graph_root(tmp_path: Path) -> Path:
    (tmp_path / "pages").mkdir(parents=True)
    return tmp_path


def test_namespace_index_groups_triple_underscore(tmp_path: Path) -> None:
    pages = tmp_path / "pages"
    pages.mkdir()
    (pages / "Wiki___Tech___Docker.md").write_text("- x\n", encoding="utf-8")
    (pages / "Other.md").write_text("- y\n", encoding="utf-8")
    cfg = MatrycaWikiConfig()
    md = build_namespace_index_markdown(tmp_path, cfg)
    assert "Wiki" in md
    assert "Wiki/Tech/Docker" in md or "[[Wiki/Tech/Docker]]" in md


def test_write_generated_hub_page_skips_on_baseline_drift(graph_root: Path) -> None:
    path = graph_safe_page_path(graph_root, MASTER_INDEX_PAGE_TITLE)
    path.write_text("- user baseline\n", encoding="utf-8")
    baseline_mtime = occ_snapshot(path)
    assert baseline_mtime is not None

    path.write_text("- user edited during compile\n", encoding="utf-8")

    result = write_generated_hub_page(
        graph_root,
        MASTER_INDEX_PAGE_TITLE,
        "- daemon compiled\n",
        baseline_mtime=baseline_mtime,
        robot_commit_summary="test hub write",
    )

    assert result.written is False
    assert path.read_text(encoding="utf-8") == "- user edited during compile\n"


def test_write_generated_hub_page_occ_abort_at_commit(
    graph_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = graph_safe_page_path(graph_root, GRAPH_INSIGHTS_TITLE)
    path.write_text("- stable insights\n", encoding="utf-8")
    baseline_mtime = occ_snapshot(path)
    assert baseline_mtime is not None

    monkeypatch.setattr(
        "src.graph.generated_hub_write.atomic_write_bytes_if_unchanged",
        lambda *_args, **_kwargs: False,
    )

    result = write_generated_hub_page(
        graph_root,
        GRAPH_INSIGHTS_TITLE,
        "- refreshed insights\n",
        baseline_mtime=baseline_mtime,
        robot_commit_summary="test hub write",
    )

    assert result.written is False
    assert path.read_text(encoding="utf-8") == "- stable insights\n"


def test_write_master_index_page_skips_on_concurrent_edit(graph_root: Path) -> None:
    path = master_index_page_path(graph_root)
    path.write_text("- user hub\n", encoding="utf-8")

    catalog = MasterCatalog(graph_root=graph_root)
    catalog.upsert(
        "Alpha",
        CatalogEntry(summary="Alpha summary", domain="risorsa", last_mtime=1),
    )

    import src.graph.master_catalog as master_catalog_mod

    original_build = master_catalog_mod.build_master_index_markdown

    def _build_and_touch(catalog: MasterCatalog) -> str:
        path.write_text("- symbiotic user edit\n", encoding="utf-8")
        return original_build(catalog)

    master_catalog_mod.build_master_index_markdown = _build_and_touch
    try:
        write_master_index_page(graph_root, catalog)
    finally:
        master_catalog_mod.build_master_index_markdown = original_build

    assert path.read_text(encoding="utf-8") == "- symbiotic user edit\n"


def test_write_graph_insights_page_skips_on_concurrent_edit(graph_root: Path) -> None:
    path = graph_safe_page_path(graph_root, GRAPH_INSIGHTS_TITLE)
    path.write_text("- user insights\n", encoding="utf-8")
    baseline_mtime = occ_snapshot(path)
    assert baseline_mtime is not None

    path.write_text("- symbiotic edit during compile\n", encoding="utf-8")

    write_graph_insights_page(
        graph_root,
        "- daemon insights\n",
        baseline_mtime=baseline_mtime,
    )

    assert path.read_text(encoding="utf-8") == "- symbiotic edit during compile\n"


def test_write_master_index_page_updates_when_quiet(graph_root: Path) -> None:
    catalog = MasterCatalog(graph_root=graph_root)
    catalog.upsert(
        "Alpha",
        CatalogEntry(summary="Alpha summary", domain="risorsa", last_mtime=1),
    )

    write_master_index_page(graph_root, catalog)

    path = master_index_page_path(graph_root)
    text = path.read_text(encoding="utf-8")
    assert "Alpha" in text
    assert "Matryca Master Index" in text
