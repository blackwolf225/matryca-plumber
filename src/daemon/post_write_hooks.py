"""Daemon adapters for graph-local page-written notifications."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from ..graph.post_write import (
    PageWrittenEvent,
    clear_page_written_handlers,
    emit_page_written,
    register_page_written_handler,
)

PostWriteEvent = PageWrittenEvent


def register_post_write_hook(handler: Callable[[PostWriteEvent], None]) -> None:
    """Register a callback invoked after each successful markdown atomic write."""
    register_page_written_handler(handler)


def clear_post_write_hooks() -> None:
    """Remove all hooks (tests)."""
    clear_page_written_handlers()


def emit_post_write_commit(
    *,
    graph_root: str | Path,
    path: str | Path,
    summary: str | None = None,
) -> None:
    """Backward-compatible alias for :func:`emit_page_written`."""
    emit_page_written(graph_root=graph_root, path=path, summary=summary)


__all__ = [
    "PostWriteEvent",
    "clear_post_write_hooks",
    "emit_post_write_commit",
    "register_post_write_hook",
]
