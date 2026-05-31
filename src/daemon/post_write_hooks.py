"""Process-wide hooks fired after successful atomic graph markdown writes."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

_hook_lock = threading.Lock()
_hooks: list[Callable[[PostWriteEvent], None]] = []


@dataclass(frozen=True, slots=True)
class PostWriteEvent:
    """Successful commit of a graph-scoped file."""

    graph_root: Path
    path: Path
    summary: str | None


def register_post_write_hook(handler: Callable[[PostWriteEvent], None]) -> None:
    """Register a callback invoked after each successful markdown atomic write."""
    with _hook_lock:
        if handler not in _hooks:
            _hooks.append(handler)


def clear_post_write_hooks() -> None:
    """Remove all hooks (tests)."""
    with _hook_lock:
        _hooks.clear()


def emit_post_write_commit(
    *,
    graph_root: str | Path,
    path: str | Path,
    summary: str | None = None,
) -> None:
    """Refresh AST cache and notify subscribers; hook failures must not propagate."""
    event = PostWriteEvent(
        graph_root=Path(graph_root).expanduser().resolve(strict=False),
        path=Path(path).expanduser().resolve(strict=False),
        summary=summary,
    )
    if event.path.suffix.lower() == ".md":
        try:
            from .ast_cache import get_graph_ast_cache

            get_graph_ast_cache(event.graph_root).apply_file_event(event.path, "modified")
        except Exception:  # noqa: BLE001
            from loguru import logger

            logger.exception("AST cache refresh failed after write to {}", event.path)
    with _hook_lock:
        handlers = list(_hooks)
    for handler in handlers:
        try:
            handler(event)
        except Exception:  # noqa: BLE001 - fail-safe for daemon/MCP stability
            from loguru import logger

            logger.exception(
                "Post-write hook failed for {} (summary={!r})",
                event.path,
                event.summary,
            )
