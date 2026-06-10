"""Tests for alias indexing and resolution."""

from __future__ import annotations

from pathlib import Path

from src.graph.alias_index import (
    build_alias_index,
    collect_relevant_alias_pages,
    format_alias_index_for_prompt,
    is_scannable_graph_markdown,
    iter_alias_source_paths,
    normalize_concept_key,
)


def test_normalize_concept_key() -> None:
    assert normalize_concept_key("  [[AI]]  ") == normalize_concept_key("ai")


def test_build_alias_index_resolves_title_and_alias(tmp_path: Path) -> None:
    pages = tmp_path / "pages"
    pages.mkdir(parents=True)
    (pages / "Artificial Intelligence.md").write_text(
        "type:: entity\nalias:: AI, [[A.I.]]\n",
        encoding="utf-8",
    )
    idx = build_alias_index(tmp_path)
    r_ai = idx.resolve("AI")
    assert r_ai.matched and r_ai.canonical_page_title == "Artificial Intelligence"
    assert r_ai.matched_via == "alias"
    r_full = idx.resolve("artificial intelligence")
    assert r_full.matched_via == "title"
    r_new = idx.resolve("Quantum Computing")
    assert r_new.safe_to_create_new_page is True


def test_collect_relevant_alias_pages_localizes_prompt_context(tmp_path: Path) -> None:
    pages = tmp_path / "pages"
    pages.mkdir(parents=True)
    (pages / "Artificial Intelligence.md").write_text(
        "type:: entity\nalias:: AI, [[A.I.]]\n",
        encoding="utf-8",
    )
    (pages / "Redis.md").write_text("type:: risorsa\n", encoding="utf-8")
    (pages / "PostgreSQL.md").write_text("type:: risorsa\n", encoding="utf-8")
    idx = build_alias_index(tmp_path)

    content = "- Learn about [[Redis]] caching patterns\n"
    relevant = collect_relevant_alias_pages(idx, content)
    assert relevant == {"Redis"}

    localized = format_alias_index_for_prompt(idx, page_content=content)
    assert "[[Redis]]" in localized
    assert "PostgreSQL" not in localized
    assert "Artificial Intelligence" not in localized

    full = format_alias_index_for_prompt(idx)
    assert "PostgreSQL" in full
    assert "Artificial Intelligence" in full


def test_build_alias_index_ignores_logseq_backup_and_recycle_clones(tmp_path: Path) -> None:
    pages = tmp_path / "pages"
    pages.mkdir(parents=True)
    (pages / "Live Page.md").write_text("alias:: live\n", encoding="utf-8")

    bak = tmp_path / "logseq" / "bak" / "pages"
    bak.mkdir(parents=True)
    (bak / "Live Page.md").write_text("alias:: ghost-backup\n", encoding="utf-8")

    recycle = tmp_path / ".recycle" / "pages"
    recycle.mkdir(parents=True)
    (recycle / "Live Page.md").write_text("alias:: ghost-recycle\n", encoding="utf-8")

    nested_bak = pages / "logseq" / "stale.md"
    nested_bak.parent.mkdir(parents=True)
    nested_bak.write_text("alias:: nested-ghost\n", encoding="utf-8")

    idx = build_alias_index(tmp_path)
    resolved = idx.resolve("live")
    assert resolved.matched
    assert resolved.canonical_page_title == "Live Page"
    assert resolved.matched_via == "alias"
    assert idx.alias_to_page.get("ghost-backup") is None
    assert idx.alias_to_page.get("ghost-recycle") is None
    assert idx.alias_to_page.get("nested-ghost") is None
    assert len(iter_alias_source_paths(tmp_path)) == 1


def test_is_scannable_graph_markdown_rejects_excluded_dirs(tmp_path: Path) -> None:
    live = tmp_path / "pages" / "ok.md"
    live.parent.mkdir(parents=True)
    live.write_text("- live\n", encoding="utf-8")
    ghost = tmp_path / "logseq" / "bak" / "pages" / "ghost.md"
    ghost.parent.mkdir(parents=True)
    ghost.write_text("- ghost\n", encoding="utf-8")

    assert is_scannable_graph_markdown(live, tmp_path) is True
    assert is_scannable_graph_markdown(ghost, tmp_path) is False


def test_build_alias_index_respects_wikilink_commas(tmp_path: Path) -> None:
    pages = tmp_path / "pages"
    pages.mkdir(parents=True)
    (pages / "Acme.md").write_text(
        "type:: entity\nalias:: [[Acme, Inc]], Acme Corp\n",
        encoding="utf-8",
    )
    idx = build_alias_index(tmp_path)
    assert idx.resolve("Acme, Inc").canonical_page_title == "Acme"
    assert idx.resolve("Acme Corp").canonical_page_title == "Acme"
