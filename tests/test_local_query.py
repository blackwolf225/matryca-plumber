"""Tests for local keyword scan."""

from __future__ import annotations

from pathlib import Path

from src.rag.local_query import (
    format_keyword_query_markdown,
    rank_pages_by_bm25,
    rank_pages_by_keyword,
)


def test_rank_pages_by_keyword(tmp_path: Path) -> None:
    pages = tmp_path / "pages"
    pages.mkdir()
    (pages / "a.md").write_text("hello world hello", encoding="utf-8")
    (pages / "b.md").write_text("world", encoding="utf-8")
    rows = rank_pages_by_keyword(tmp_path, "hello", limit=10)
    assert rows[0][0].endswith("a.md")
    assert rows[0][1] == 2


def test_rank_pages_by_bm25_orders_by_relevance(tmp_path: Path) -> None:
    pages = tmp_path / "pages"
    pages.mkdir()
    (pages / "sparse.md").write_text("cat", encoding="utf-8")
    (pages / "dense.md").write_text("cat dog cat dog cat page", encoding="utf-8")

    rows = rank_pages_by_bm25(tmp_path, "cat dog", limit=10)
    assert rows[0][0].endswith("dense.md")


def test_format_keyword_query_markdown(tmp_path: Path) -> None:
    (tmp_path / "pages").mkdir()
    (tmp_path / "pages" / "z.md").write_text("banana", encoding="utf-8")
    md = format_keyword_query_markdown(tmp_path, "banana")
    assert "banana" in md
    assert "BM25" in md


def test_format_keyword_substring_mode(tmp_path: Path) -> None:
    (tmp_path / "pages").mkdir()
    (tmp_path / "pages" / "z.md").write_text("banana banana", encoding="utf-8")
    md = format_keyword_query_markdown(tmp_path, "banana", mode="substring")
    assert "substring" in md.lower() or "Substring" in md
