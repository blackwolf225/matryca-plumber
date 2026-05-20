"""Per-file write locks serializing Read-Modify-Write cycles across threads and processes."""

from __future__ import annotations

import os
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

_fcntl: Any
try:
    import fcntl as _fcntl
except ImportError:  # pragma: no cover - Windows and other non-Unix platforms
    _fcntl = None

_registry_guard = threading.Lock()
_page_locks: dict[str, threading.Lock] = {}


def normalize_page_lock_key(page_path: str | Path) -> str:
    """Return a stable absolute path string used as the lock registry key."""
    return str(Path(page_path).expanduser().resolve(strict=False))


def _sidecar_lock_path(page_path: str | Path) -> Path:
    """Return a hidden lock file adjacent to the target (same directory, one volume)."""
    path = Path(page_path).expanduser().resolve(strict=False)
    return path.parent / f".{path.name}.matryca.lock"


def _lock_for_key(key: str) -> threading.Lock:
    with _registry_guard:
        lock = _page_locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _page_locks[key] = lock
        return lock


@contextmanager
def _cross_process_file_lock(page_path: str | Path) -> Iterator[None]:
    """Exclusive ``fcntl.flock`` on a sidecar lock file (no-op when ``fcntl`` is unavailable)."""
    if _fcntl is None:
        yield
        return

    lock_path = _sidecar_lock_path(page_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
    try:
        _fcntl.flock(fd, _fcntl.LOCK_EX)
        try:
            yield
        finally:
            _fcntl.flock(fd, _fcntl.LOCK_UN)
    finally:
        os.close(fd)


@contextmanager
def page_rmw_lock(page_path: str | Path) -> Iterator[None]:
    """Hold an exclusive lock for one file's full RMW lifecycle (thread- and process-safe)."""
    key = normalize_page_lock_key(page_path)
    thread_lock = _lock_for_key(key)
    thread_lock.acquire()
    try:
        with _cross_process_file_lock(page_path):
            yield
    finally:
        thread_lock.release()


def clear_page_write_locks() -> None:
    """Drop the in-process lock registry (for tests)."""
    with _registry_guard:
        _page_locks.clear()


def cross_process_lock_available() -> bool:
    """Return whether OS-level ``flock`` locking is active on this platform."""
    return _fcntl is not None and sys.platform != "win32"


__all__ = [
    "clear_page_write_locks",
    "cross_process_lock_available",
    "normalize_page_lock_key",
    "page_rmw_lock",
]
