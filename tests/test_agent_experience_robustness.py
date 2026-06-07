"""Agent-experience robustness: namespace normalization and safe write fallbacks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from src.agent.graph_dispatch import dispatch_mutate, dispatch_read
from src.agent.graph_tool_helpers import read_block_ast_markdown
from src.agent.page_input_normalizer import normalize_page_ref, normalize_page_ref_or_raw
from src.config import MatrycaWikiConfig


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
