"""Phase 8: global fence scanner, transactional writes, generational caches."""

from __future__ import annotations

import time
from pathlib import Path

from src.graph.generational_cache import (
    Bm25Corpus,
    cached_build_alias_index,
    clear_generational_caches,
    get_cached_bm25_corpus,
    score_bm25_query,
)
from src.graph.global_fence_scanner import compute_page_protected_line_indices
from src.graph.markdown_blocks import atomic_write_bytes
from src.graph.property_line_edit import edit_block_property_lines
from src.graph.reparent_blocks import refactor_logseq_blocks
from src.graph.tag_unify import unify_tags_in_text
from src.graph.unlinked_mentions import resolve_unlinked_mentions


def test_fence_multiline_code_block() -> None:
    md = "```\nline1\nline2\n```\n- ok\n"
    p = compute_page_protected_line_indices(md)
    assert 0 in p and 1 in p and 2 in p and 3 in p
    assert 4 not in p


def test_fence_masks_query_and_html_inside() -> None:
    md = "\n".join(
        [
            "```",
            "#+BEGIN_QUERY",
            "<!--",
            "#+END_QUERY",
            "-->",
            "```",
            "#+BEGIN_QUERY",
            ":query []",
            "#+END_QUERY",
            "",
        ],
    )
    p = compute_page_protected_line_indices(md)
    assert 0 in p  # opening ```
    assert 1 in p  # fake BEGIN inside code
    assert 6 in p  # real BEGIN
    assert 7 in p and 8 in p


def test_html_comment_multiline() -> None:
    md = "ok\n<!--\nhidden\n-->\nvisible\n"
    p = compute_page_protected_line_indices(md)
    assert 1 in p and 2 in p and 3 in p
    assert 0 not in p and 4 not in p


def test_empty_fence_opener_and_closer_lines_protected() -> None:
    md = "```\n```\nnext\n"
    p = compute_page_protected_line_indices(md)
    assert 0 in p and 1 in p
    assert 2 not in p


def test_atomic_write_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "sub" / "page.md"
    atomic_write_bytes(p, b"hello", graph_root=tmp_path)
    assert p.read_bytes() == b"hello"
    atomic_write_bytes(p, b"world", graph_root=tmp_path)
    assert p.read_bytes() == b"world"


def test_alias_cache_invalidates_on_mtime(tmp_path: Path) -> None:
    clear_generational_caches()
    pages = tmp_path / "pages"
    pages.mkdir(parents=True)
    f = pages / "P.md"
    f.write_text("alias:: X\n", encoding="utf-8")
    a1 = cached_build_alias_index(tmp_path)
    assert a1.resolve("X").matched
    time.sleep(0.02)
    f.write_text("alias:: Y\n", encoding="utf-8")
    a2 = cached_build_alias_index(tmp_path)
    assert a2.resolve("Y").matched
    assert not a2.resolve("X").matched


def test_bm25_corpus_cache_and_score(tmp_path: Path) -> None:
    clear_generational_caches()
    pages = tmp_path / "pages"
    pages.mkdir()
    (pages / "a.md").write_text("cat dog", encoding="utf-8")
    c1 = get_cached_bm25_corpus(tmp_path)
    c2 = get_cached_bm25_corpus(tmp_path)
    assert isinstance(c1, Bm25Corpus)
    assert c1.n_docs == c2.n_docs
    rows = score_bm25_query(c1, "cat", limit=5)
    assert rows and rows[0][0].endswith("a.md")


def test_property_edit_rejects_protected_line(tmp_path: Path) -> None:
    uid = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    pages = tmp_path / "pages"
    pages.mkdir()
    md = "\n".join(
        [
            "```",
            "- block",
            f"  id:: {uid}",
            "  type:: alpha",
            "```",
            "",
        ],
    )
    (pages / "X.md").write_text(md, encoding="utf-8")
    out = edit_block_property_lines(
        tmp_path,
        "X",
        uid,
        "alpha",
        "beta",
        dry_run=True,
    )
    assert not out.ok and out.code == "protected_fence"


def test_unify_tags_skips_protected_line() -> None:
    raw = "#foo\n```\n#foo\n```\n"
    dead = compute_page_protected_line_indices(raw)
    new, n = unify_tags_in_text(raw, {"#foo": "#FOO"}, protected_line_indices=dead)
    assert n == 1
    assert new.splitlines()[0] == "#FOO"


def test_reparent_rejects_block_in_fence(tmp_path: Path) -> None:
    pages = tmp_path / "pages"
    pages.mkdir()
    u1 = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    u2 = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
    md = "\n".join(
        [
            "```",
            "- one",
            f"  id:: {u1}",
            "- two",
            f"  id:: {u2}",
            "```",
            "",
        ],
    )
    (pages / "R.md").write_text(md, encoding="utf-8")
    out = refactor_logseq_blocks(
        tmp_path,
        "R",
        [{"category": "Cat", "block_uuids": [u1]}],
        dry_run=True,
    )
    assert not out.ok and out.code == "protected_fence"


def test_unlinked_mentions_skips_fenced_lines(tmp_path: Path) -> None:
    clear_generational_caches()
    pages = tmp_path / "pages"
    pages.mkdir()
    (pages / "My Topic.md").write_text("x\n", encoding="utf-8")
    md = "\n".join(
        [
            "My Topic is discussed here in prose.",
            "```",
            "My Topic should not count",
            "```",
            "",
        ],
    )
    (pages / "Note.md").write_text(md, encoding="utf-8")
    r = resolve_unlinked_mentions(tmp_path, max_hits_per_file=20, max_titles=100)
    hits = r["hits"]
    assert isinstance(hits, list)
    fenced_hits = [h for h in hits if h.get("line_number") in (2, 3, 4)]
    assert not fenced_hits
