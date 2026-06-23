"""Graph-local port for post-write notifications (no daemon imports)."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

_hook_lock = threading.Lock()
_handlers: list[Callable[[PageWrittenEvent], None]] = []


@dataclass(frozen=True, slots=True)
class PageWrittenEvent:
    """Successful commit of a graph-scoped file."""

    graph_root: Path
    path: Path
    summary: str | None


def register_page_written_handler(handler: Callable[[PageWrittenEvent], None]) -> None:
    """Register a callback invoked after each successful markdown atomic write."""
    with _hook_lock:
        if handler not in _handlers:
            _handlers.append(handler)


def clear_page_written_handlers() -> None:
    """Remove all handlers (tests)."""
    with _hook_lock:
        _handlers.clear()


def emit_page_written(
    *,
    graph_root: str | Path,
    path: str | Path,
    summary: str | None = None,
) -> None:
    """Notify subscribers; handler failures must not propagate."""
    event = PageWrittenEvent(
        graph_root=Path(graph_root).expanduser().resolve(strict=False),
        path=Path(path).expanduser().resolve(strict=False),
        summary=summary,
    )
    with _hook_lock:
        handlers = list(_handlers)
    for handler in handlers:
        try:
            handler(event)
        except Exception:  # noqa: BLE001 - fail-safe for daemon/MCP stability
            from loguru import logger

            logger.exception(
                "Page-written handler failed for {} (summary={!r})",
                event.path,
                event.summary,
            )


__all__ = [
    "PageWrittenEvent",
    "clear_page_written_handlers",
    "emit_page_written",
    "register_page_written_handler",
]
