"""Debounced watchdog observer for Logseq ``pages/`` and ``journals/``."""

from __future__ import annotations

import os
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from loguru import logger
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from ..graph.alias_index import is_scannable_graph_markdown
from ..graph.path_sandbox import assert_path_within_graph

FileEventKind = Literal["created", "modified", "deleted"]

_DEFAULT_DEBOUNCE_MS = 750
_MIN_DEBOUNCE_MS = 500
_MAX_DEBOUNCE_MS = 1000


def _debounce_ms_from_env() -> float:
    raw = os.environ.get("MATRYCA_WATCH_DEBOUNCE_MS", str(_DEFAULT_DEBOUNCE_MS)).strip()
    try:
        ms = int(raw)
    except ValueError:
        ms = _DEFAULT_DEBOUNCE_MS
    return float(max(_MIN_DEBOUNCE_MS, min(_MAX_DEBOUNCE_MS, ms)) / 1000.0)


def _event_kind(event: FileSystemEvent) -> FileEventKind | None:
    if event.is_directory:
        return None
    if event.event_type == "created":
        return "created"
    if event.event_type == "modified":
        return "modified"
    if event.event_type == "deleted":
        return "deleted"
    return None


class _DebouncedMarkdownHandler(FileSystemEventHandler):
    def __init__(
        self,
        graph_root: Path,
        *,
        debounce_s: float,
        on_debounced: Callable[[Path, FileEventKind], None],
    ) -> None:
        super().__init__()
        self._graph_root = graph_root
        self._debounce_s = debounce_s
        self._on_debounced = on_debounced
        self._timers: dict[str, threading.Timer] = {}
        self._timer_lock = threading.Lock()

    def _schedule(self, path: Path, kind: FileEventKind) -> None:
        key = str(path)
        with self._timer_lock:
            existing = self._timers.pop(key, None)
            if existing is not None:
                existing.cancel()

            def fire() -> None:
                with self._timer_lock:
                    self._timers.pop(key, None)
                try:
                    self._on_debounced(path, kind)
                except Exception:  # noqa: BLE001
                    logger.exception("Debounced file watcher callback failed for {}", path)

            timer = threading.Timer(self._debounce_s, fire)
            timer.daemon = True
            self._timers[key] = timer
            timer.start()

    def on_created(self, event: FileSystemEvent) -> None:
        self._handle(event)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._handle(event)

    def on_deleted(self, event: FileSystemEvent) -> None:
        self._handle(event)

    def _handle(self, event: FileSystemEvent) -> None:
        kind = _event_kind(event)
        if kind is None:
            return
        src = getattr(event, "src_path", None)
        if not src:
            return
        path = Path(src)
        if path.suffix.lower() != ".md":
            return
        try:
            safe = assert_path_within_graph(path, self._graph_root)
        except Exception:  # noqa: BLE001
            return
        if kind != "deleted" and not is_scannable_graph_markdown(safe, self._graph_root):
            return
        self._schedule(safe, kind)

    def cancel_all(self) -> None:
        with self._timer_lock:
            for timer in self._timers.values():
                timer.cancel()
            self._timers.clear()


class GraphFileWatcher:
    """Watch ``pages/`` and ``journals/`` under a Logseq graph root."""

    def __init__(
        self,
        graph_root: Path,
        *,
        on_debounced_change: Callable[[Path, FileEventKind], None],
        debounce_s: float | None = None,
    ) -> None:
        self._graph_root = graph_root.expanduser().resolve(strict=False)
        self._on_debounced_change = on_debounced_change
        self._debounce_s = debounce_s if debounce_s is not None else _debounce_ms_from_env()
        self._observer: Observer | None = None  # type: ignore[valid-type]
        self._handler: _DebouncedMarkdownHandler | None = None

    def start(self) -> None:
        if self._observer is not None:
            return
        handler = _DebouncedMarkdownHandler(
            self._graph_root,
            debounce_s=self._debounce_s,
            on_debounced=self._on_debounced_change,
        )
        observer = Observer()
        for subdir in ("pages", "journals"):
            watch_path = self._graph_root / subdir
            if watch_path.is_dir():
                observer.schedule(handler, str(watch_path), recursive=True)
                logger.bind(path=str(watch_path)).info("Watching graph markdown directory")
        observer.start()
        self._handler = handler
        self._observer = observer

    def stop(self) -> None:
        if self._handler is not None:
            self._handler.cancel_all()
            self._handler = None
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5.0)
            self._observer = None


__all__ = ["FileEventKind", "GraphFileWatcher"]
