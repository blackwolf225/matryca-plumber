"""Tests for debounced graph file watcher."""

from __future__ import annotations

import threading
import time
from pathlib import Path

from src.daemon.file_watcher import _DebouncedMarkdownHandler


def test_debounce_coalesces_rapid_events(tmp_path: Path) -> None:
    pages = tmp_path / "pages"
    pages.mkdir()
    path = pages / "note.md"
    path.write_text("- a\n", encoding="utf-8")

    events: list[tuple[Path, str]] = []
    lock = threading.Lock()

    def on_fire(p: Path, kind: str) -> None:
        with lock:
            events.append((p, kind))

    handler = _DebouncedMarkdownHandler(
        tmp_path,
        debounce_s=0.05,
        on_debounced=on_fire,
    )

    class _Ev:
        is_directory = False
        event_type = "modified"
        src_path = str(path)

    handler.on_modified(_Ev())  # type: ignore[arg-type]
    handler.on_modified(_Ev())  # type: ignore[arg-type]
    time.sleep(0.2)
    handler.cancel_all()

    with lock:
        assert len(events) == 1
        assert events[0][1] == "modified"
