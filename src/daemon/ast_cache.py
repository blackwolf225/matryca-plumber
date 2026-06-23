"""Backward-compatible re-exports — canonical module: ``graph.ast_cache``."""

from __future__ import annotations

from ..graph.ast_cache import (
    FileEventKind,
    GraphAstCache,
    clear_graph_ast_cache,
    count_graph_markdown_files,
    get_graph_ast_cache,
)

__all__ = [
    "FileEventKind",
    "GraphAstCache",
    "clear_graph_ast_cache",
    "count_graph_markdown_files",
    "get_graph_ast_cache",
]
