"""Tests for structural hop graph (wikilinks, tags, schema rings)."""

from __future__ import annotations

from pathlib import Path

from src.graph.link_tag_hop import (
    bfs_hops,
    build_structural_graph,
    format_hop_report_markdown,
    format_hub_orphan_markdown,
    structural_degrees,
)


def test_wikilink_edge(tmp_path: Path) -> None:
    pages = tmp_path / "pages"
    pages.mkdir(parents=True)
    (pages / "Alpha.md").write_text("See [[Beta]] and [[Gamma]]", encoding="utf-8")
    (pages / "Beta.md").write_text("back [[Alpha]]", encoding="utf-8")
    (pages / "Gamma.md").write_text("lonely", encoding="utf-8")

    g = build_structural_graph(tmp_path)
    alpha_n = {n for (n, _) in g.get("Alpha", ())}
    assert "Beta" in alpha_n and "Gamma" in alpha_n


def test_tag_clique(tmp_path: Path) -> None:
    pages = tmp_path / "pages"
    pages.mkdir(parents=True)
    (pages / "A.md").write_text("hello #shared", encoding="utf-8")
    (pages / "B.md").write_text("#shared world", encoding="utf-8")

    g = build_structural_graph(tmp_path)
    assert ("B", "tag") in g.get("A", ())
    assert ("A", "tag") in g.get("B", ())


def test_bfs_respects_max_per_level(tmp_path: Path) -> None:
    pages = tmp_path / "pages"
    pages.mkdir(parents=True)
    hub = "Hub.md"
    (pages / hub).write_text("\n".join(f"[[N{i}]]" for i in range(10)), encoding="utf-8")
    for i in range(10):
        (pages / f"N{i}.md").write_text("x", encoding="utf-8")

    levels, edges = bfs_hops(tmp_path, ["Hub"], max_depth=1, max_per_level=3)
    assert len(levels) == 2
    new = levels[1]["new"]
    assert isinstance(new, list)
    assert len(new) <= 3
    assert len(edges) <= 3


def test_structural_degrees(tmp_path: Path) -> None:
    pages = tmp_path / "pages"
    pages.mkdir(parents=True)
    (pages / "X.md").write_text("[[Y]]", encoding="utf-8")
    (pages / "Y.md").write_text("[[X]]", encoding="utf-8")
    d = structural_degrees(tmp_path)
    assert d["X"] == 1 and d["Y"] == 1


def test_format_reports(tmp_path: Path) -> None:
    pages = tmp_path / "pages"
    pages.mkdir(parents=True)
    (pages / "P.md").write_text("[[Q]]\ntype:: knowledge", encoding="utf-8")
    (pages / "Q.md").write_text("type:: knowledge", encoding="utf-8")

    hop = format_hop_report_markdown(tmp_path, ["P"], max_depth=2, max_per_level=10)
    assert "Structural hop" in hop
    assert "P" in hop

    ho = format_hub_orphan_markdown(tmp_path, hub_limit=5, orphan_limit=5)
    assert "Hub" in ho or "hub" in ho.lower()
