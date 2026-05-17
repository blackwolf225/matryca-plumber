"""Tests for alias indexing and resolution."""

from __future__ import annotations

from pathlib import Path

from src.graph.alias_index import build_alias_index, normalize_concept_key


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
