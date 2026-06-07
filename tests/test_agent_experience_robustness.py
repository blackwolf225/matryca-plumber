"""Agent-experience robustness: namespace normalization and safe write fallbacks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from src.agent.graph_dispatch import _coerce_write_target, dispatch_mutate, dispatch_read
from src.agent.graph_tool_helpers import read_block_ast_markdown
from src.agent.page_input_normalizer import (
    UNSAFE_PAGE_REF_MSG,
    normalize_page_ref,
    normalize_page_ref_or_raw,
)
from src.config import MatrycaWikiConfig
from src.graph.page_path import page_title_to_filename


def _seed_namespaced_page(tmp_path: Path) -> tuple[str, str]:
    """Create ``progetti/Matryca.ai`` on disk; return parent and child block UUIDs."""
    pages = tmp_path / "pages"
    pages.mkdir()
    parent_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    child_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    (pages / "progetti___Matryca.ai.md").write_text(
        f"- Title block\n  id:: {parent_id}\n- Bottom block\n  id:: {child_id}\n",
        encoding="utf-8",
    )
    return parent_id, child_id


@pytest.mark.parametrize(
    ("raw", "expected_title"),
    [
        ("progetti/Matryca.ai", "progetti/Matryca.ai"),
        ("progetti___Matryca.ai", "progetti/Matryca.ai"),
        ("progetti___Matryca.ai.md", "progetti/Matryca.ai"),
        ("pages/progetti___Matryca.ai.md", "progetti/Matryca.ai"),
        ("PROGETTI/matryca.ai", "progetti/Matryca.ai"),
    ],
)
def test_normalize_page_ref_namespace_and_casing_variants(
    tmp_path: Path,
    raw: str,
    expected_title: str,
) -> None:
    _seed_namespaced_page(tmp_path)
    resolved = normalize_page_ref(tmp_path, raw)
    assert resolved is not None
    assert resolved.canonical_title == expected_title


def test_normalize_page_ref_or_raw_sanitizes_without_match(tmp_path: Path) -> None:
    out = normalize_page_ref_or_raw(tmp_path, " pages/NewPage.md ")
    assert out.canonical_title == "NewPage"
    assert any(".md" in note for note in out.resolution_notes)


@pytest.mark.asyncio
async def test_dispatch_read_page_lenient_namespace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_namespaced_page(tmp_path)
    monkeypatch.setenv("LOGSEQ_GRAPH_PATH", str(tmp_path))
    body = await dispatch_read(MatrycaWikiConfig(), "page", "progetti___Matryca.ai.md")
    assert "Title block" in body
    assert "Page resolution notes" in body


def test_read_block_ast_with_underscore_namespace_page_ref(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent_id, _ = _seed_namespaced_page(tmp_path)
    monkeypatch.setenv("LOGSEQ_GRAPH_PATH", str(tmp_path))
    md = read_block_ast_markdown(
        str(tmp_path),
        f"progetti___Matryca.ai.md|{parent_id}",
    )
    assert "Title block" in md
    assert parent_id in md


@pytest.mark.asyncio
async def test_write_outline_safe_fallback_invalid_uuid_on_existing_page(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_namespaced_page(tmp_path)
    monkeypatch.setenv("LOGSEQ_GRAPH_PATH", str(tmp_path))
    bad_uuid = "deadbeef-dead-beef-dead-beefdeadbeef"
    outline: dict[str, Any] = {"text": "Recovered outline block", "children": []}
    out = await dispatch_mutate(
        "write_outline",
        f"progetti/Matryca.ai|{bad_uuid}",
        __import__("json").dumps(outline),
    )
    assert out.get("ok") is True
    warnings = out.get("warnings") or []
    assert any("safe append" in str(note).lower() for note in warnings)
    page_text = (tmp_path / "pages" / "progetti___Matryca.ai.md").read_text(encoding="utf-8")
    assert "Recovered outline block" in page_text


@pytest.mark.asyncio
async def test_write_outline_safe_fallback_unknown_alias_with_page_pipe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_namespaced_page(tmp_path)
    monkeypatch.setenv("LOGSEQ_GRAPH_PATH", str(tmp_path))
    outline: dict[str, Any] = {"text": "Alias fallback block", "children": []}
    out = await dispatch_mutate(
        "write_outline",
        "progetti___Matryca.ai|[0]",
        __import__("json").dumps(outline),
    )
    assert out.get("ok") is True
    warnings = out.get("warnings") or []
    assert any("safe append" in str(note).lower() for note in warnings)
    page_text = (tmp_path / "pages" / "progetti___Matryca.ai.md").read_text(encoding="utf-8")
    assert "Alias fallback block" in page_text


@pytest.mark.asyncio
async def test_write_outline_unknown_alias_without_page_still_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_namespaced_page(tmp_path)
    monkeypatch.setenv("LOGSEQ_GRAPH_PATH", str(tmp_path))
    out = await dispatch_mutate(
        "write_outline",
        "[42]",
        '{"text":"x","children":[]}',
    )
    assert out.get("ok") is False
    assert "[42]" in str(out.get("error"))


# --- Chaos Monkey: namespace normalizer edge cases ---


@pytest.mark.parametrize("raw", ["", "   ", "\t\n"])
def test_normalize_page_ref_rejects_blank_input(tmp_path: Path, raw: str) -> None:
    assert normalize_page_ref(tmp_path, raw) is None
    blank = normalize_page_ref_or_raw(tmp_path, raw)
    assert blank.canonical_title == ""


@pytest.mark.parametrize(
    "raw",
    [
        "../../etc/passwd",
        "progetti/../../Lancio",
        "/etc/passwd",
    ],
)
def test_normalize_page_ref_rejects_path_traversal(tmp_path: Path, raw: str) -> None:
    with pytest.raises(ValueError, match="path traversal"):
        normalize_page_ref(tmp_path, raw)
    with pytest.raises(ValueError, match="path traversal"):
        normalize_page_ref_or_raw(tmp_path, raw)


@pytest.mark.asyncio
async def test_dispatch_read_rejects_path_traversal_gracefully(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOGSEQ_GRAPH_PATH", str(tmp_path))
    body = await dispatch_read(MatrycaWikiConfig(), "page", "../../etc/passwd")
    assert UNSAFE_PAGE_REF_MSG in body


def test_normalize_page_ref_collapses_triple_slash(tmp_path: Path) -> None:
    _seed_namespaced_page(tmp_path)
    resolved = normalize_page_ref(tmp_path, "progetti///Matryca.ai")
    assert resolved is not None
    assert resolved.canonical_title == "progetti/Matryca.ai"


def test_normalize_page_ref_strips_repeated_md_suffixes(tmp_path: Path) -> None:
    pages = tmp_path / "pages"
    pages.mkdir()
    (pages / "progetti___Lancio.md").write_text("- note\n", encoding="utf-8")
    resolved = normalize_page_ref(tmp_path, "progetti.md/Lancio.md.md")
    assert resolved is not None
    assert resolved.canonical_title == "progetti/Lancio"


def test_normalize_page_ref_special_logseq_title_chars(tmp_path: Path) -> None:
    title = "progetti/Q&A - 2026!"
    pages = tmp_path / "pages"
    pages.mkdir()
    (pages / page_title_to_filename(title)).write_text("- special\n", encoding="utf-8")
    resolved = normalize_page_ref(tmp_path, title)
    assert resolved is not None
    assert resolved.canonical_title == title


# --- Chaos Monkey: safe fallback write targets ---


def test_coerce_write_target_accepts_int_zero() -> None:
    assert _coerce_write_target(0) == "0"


@pytest.mark.asyncio
async def test_write_outline_bare_zero_target_fails_gracefully(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_namespaced_page(tmp_path)
    monkeypatch.setenv("LOGSEQ_GRAPH_PATH", str(tmp_path))
    out = await dispatch_mutate(
        "write_outline",
        "0",
        '{"text":"x","children":[]}',
    )
    assert out.get("ok") is False
    assert "No node registered" in str(out.get("error"))


@pytest.mark.asyncio
async def test_write_outline_page_pipe_zero_string_uses_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_namespaced_page(tmp_path)
    monkeypatch.setenv("LOGSEQ_GRAPH_PATH", str(tmp_path))
    outline: dict[str, Any] = {"text": "From string zero", "children": []}
    out = await dispatch_mutate(
        "write_outline",
        "progetti/Matryca.ai|0",
        json.dumps(outline),
    )
    assert out.get("ok") is True
    page_text = (tmp_path / "pages" / "progetti___Matryca.ai.md").read_text(encoding="utf-8")
    assert "From string zero" in page_text


@pytest.mark.asyncio
async def test_write_outline_random_string_without_page_fails_gracefully(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_namespaced_page(tmp_path)
    monkeypatch.setenv("LOGSEQ_GRAPH_PATH", str(tmp_path))
    out = await dispatch_mutate(
        "write_outline",
        "non-un-uuid-ne-un-alias",
        '{"text":"x","children":[]}',
    )
    assert out.get("ok") is False
    assert "No node registered" in str(out.get("error"))


@pytest.mark.asyncio
async def test_write_outline_valid_uuid_format_but_missing_uses_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_namespaced_page(tmp_path)
    monkeypatch.setenv("LOGSEQ_GRAPH_PATH", str(tmp_path))
    missing = "cccccccc-cccc-cccc-cccc-cccccccccccc"
    outline: dict[str, Any] = {"text": "Valid-format missing uuid", "children": []}
    out = await dispatch_mutate(
        "write_outline",
        f"progetti/Matryca.ai|{missing}",
        json.dumps(outline),
    )
    assert out.get("ok") is True
    assert any("safe append" in str(note).lower() for note in (out.get("warnings") or []))


@pytest.mark.asyncio
async def test_write_outline_random_string_with_page_pipe_uses_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_namespaced_page(tmp_path)
    monkeypatch.setenv("LOGSEQ_GRAPH_PATH", str(tmp_path))
    outline: dict[str, Any] = {"text": "Random target fallback", "children": []}
    out = await dispatch_mutate(
        "write_outline",
        "progetti/Matryca.ai|non-un-uuid-ne-un-alias",
        json.dumps(outline),
    )
    assert out.get("ok") is True
    page_text = (tmp_path / "pages" / "progetti___Matryca.ai.md").read_text(encoding="utf-8")
    assert "Random target fallback" in page_text


@pytest.mark.asyncio
async def test_write_outline_empty_page_file_appends_at_eof(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pages = tmp_path / "pages"
    pages.mkdir()
    (pages / "progetti___Empty.md").write_bytes(b"")
    monkeypatch.setenv("LOGSEQ_GRAPH_PATH", str(tmp_path))
    outline: dict[str, Any] = {"text": "First block on empty page", "children": []}
    out = await dispatch_mutate(
        "write_outline",
        "progetti/Empty|deadbeef-dead-beef-dead-beefdeadbeef",
        json.dumps(outline),
    )
    assert out.get("ok") is True
    page_text = (pages / "progetti___Empty.md").read_text(encoding="utf-8")
    assert "First block on empty page" in page_text
    assert "id::" in page_text


@pytest.mark.asyncio
async def test_write_outline_zero_byte_page_with_whitespace_only_appends(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pages = tmp_path / "pages"
    pages.mkdir()
    (pages / "Whitespace.md").write_text("   \n\n", encoding="utf-8")
    monkeypatch.setenv("LOGSEQ_GRAPH_PATH", str(tmp_path))
    outline: dict[str, Any] = {"text": "Whitespace recovery", "children": []}
    out = await dispatch_mutate(
        "write_outline",
        "Whitespace|not-a-real-block",
        json.dumps(outline),
    )
    assert out.get("ok") is True
    page_text = (pages / "Whitespace.md").read_text(encoding="utf-8")
    assert "Whitespace recovery" in page_text
