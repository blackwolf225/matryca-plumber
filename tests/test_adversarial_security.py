"""Adversarial tests: path traversal sandbox and MCP tool guard."""

from __future__ import annotations

from pathlib import Path

import pytest
from src.agent.mcp_tool_guard import guard_mcp_tool
from src.graph.markdown_blocks import atomic_write_bytes, graph_safe_page_path
from src.graph.path_sandbox import (
    SECURITY_VIOLATION_MSG,
    PathTraversalSecurityError,
    assert_path_within_graph,
    normalize_daemon_file_key,
)
from src.rag.matryca_hooks import resolve_logseq_page_md


def _make_graph(tmp_path: Path) -> Path:
    graph = tmp_path / "graph"
    (graph / "pages").mkdir(parents=True)
    return graph


def test_normalize_daemon_file_key_resolves_dotdot_inside_graph(tmp_path: Path) -> None:
    graph = tmp_path / "graph"
    (graph / "pages").mkdir(parents=True)
    page = graph / "pages" / "Safe.md"
    page.write_text("- ok\n", encoding="utf-8")
    key = normalize_daemon_file_key(graph, "pages/../pages/Safe.md")
    assert key == "pages/Safe.md"


def test_normalize_daemon_file_key_rejects_dotdot_escape(tmp_path: Path) -> None:
    graph = tmp_path / "graph"
    (graph / "pages").mkdir(parents=True)
    outside = tmp_path / "outside.md"
    outside.write_text("x", encoding="utf-8")
    key = normalize_daemon_file_key(graph, f"pages/../../{outside.name}")
    assert key == ""


def test_graph_safe_page_path_blocks_dotdot_page_ref(tmp_path: Path) -> None:
    graph = _make_graph(tmp_path)
    with pytest.raises(PathTraversalSecurityError, match="Security Violation"):
        graph_safe_page_path(graph, "../../../etc/passwd")


def test_graph_safe_page_path_blocks_pages_prefix_escape(tmp_path: Path) -> None:
    graph = _make_graph(tmp_path)
    with pytest.raises(PathTraversalSecurityError, match="Security Violation"):
        graph_safe_page_path(graph, "pages/../../outside.md")


def test_atomic_write_bytes_blocks_path_outside_graph(tmp_path: Path) -> None:
    graph = _make_graph(tmp_path)
    outside = tmp_path / "escape.md"
    with pytest.raises(PathTraversalSecurityError, match="Security Violation"):
        atomic_write_bytes(outside, b"owned", graph_root=graph)


def test_assert_path_within_graph_allows_in_graph_file(tmp_path: Path) -> None:
    graph = _make_graph(tmp_path)
    inside = graph / "pages" / "Safe.md"
    inside.write_text("- ok\n", encoding="utf-8")
    resolved = assert_path_within_graph(inside, graph)
    assert resolved == inside.resolve()


def test_resolve_logseq_page_md_blocks_traversal_before_lookup(tmp_path: Path) -> None:
    graph = _make_graph(tmp_path)
    with pytest.raises(PathTraversalSecurityError, match="Security Violation"):
        resolve_logseq_page_md(graph, "../../outside")


@pytest.mark.asyncio
async def test_guard_mcp_tool_surfaces_path_traversal_value_error() -> None:
    @guard_mcp_tool
    async def blocked() -> dict[str, object]:
        raise PathTraversalSecurityError(SECURITY_VIOLATION_MSG)

    out = await blocked()
    assert out["ok"] is False
    assert out["code"] == "security_violation"
    assert "Security Violation" in str(out["error"])
