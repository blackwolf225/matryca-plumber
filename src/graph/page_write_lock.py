"""Per-file write locks serializing Read-Modify-Write cycles across threads and processes."""

from __future__ import annotations

import sys
import threading
import time
from collections import OrderedDict
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from loguru import logger

from ..utils.platform_lock import (
    _fcntl,
    cross_process_sidecar_lock,
    probe_exclusive_flock,
)
from .io_retry import (
    IO_RETRY_ATTEMPTS,
    IO_RETRY_INITIAL_DELAY_S,
    IO_RETRY_MAX_DELAY_S,
    PageLockUnavailableError,
)

_registry_guard = threading.Lock()
_page_locks: OrderedDict[str, threading.RLock] = OrderedDict()
_MAX_PAGE_LOCK_REGISTRY = 4096


def normalize_page_lock_key(page_path: str | Path) -> str:
    """Return a stable absolute path string used as the lock registry key."""
    return str(Path(page_path).expanduser().resolve(strict=False))


def _sidecar_lock_path(page_path: str | Path) -> Path:
    """Return a hidden lock file adjacent to the target (same directory, one volume)."""
    path = Path(page_path).expanduser().resolve(strict=False)
    return path.parent / f".{path.name}.matryca.lock"


def _lock_for_key(key: str) -> threading.RLock:
    with _registry_guard:
        lock = _page_locks.get(key)
        if lock is not None:
            _page_locks.move_to_end(key)
            return lock
        while len(_page_locks) >= _MAX_PAGE_LOCK_REGISTRY:
            evicted = False
            for old_key in list(_page_locks):
                old_lock = _page_locks[old_key]
                if not getattr(old_lock, "locked", lambda: False)():
                    del _page_locks[old_key]
                    evicted = True
                    break
            if not evicted:
                raise PageLockUnavailableError(
                    f"In-process page lock registry full ({_MAX_PAGE_LOCK_REGISTRY}); "
                    f"cannot register lock for {key}",
                )
        lock = threading.RLock()
        _page_locks[key] = lock
        return lock


@contextmanager
def _cross_process_file_lock(page_path: str | Path) -> Iterator[None]:
    """Exclusive ``fcntl.flock`` on a sidecar lock file (no-op when ``fcntl`` is unavailable)."""
    key = normalize_page_lock_key(page_path)
    lock_path = _sidecar_lock_path(page_path)
    with cross_process_sidecar_lock(
        lock_path,
        depth_key=key,
        unavailable_label="page lock",
    ):
        yield


def probe_page_rmw_lock(page_path: str | Path) -> None:
    """Verify the page lock can be acquired without holding it through long work.

    Raises:
        PageLockUnavailableError: When thread or cross-process locks are contended.
    """
    key = normalize_page_lock_key(page_path)
    thread_lock = _lock_for_key(key)
    if not thread_lock.acquire(blocking=False):
        raise PageLockUnavailableError(
            f"Could not probe in-process page lock for {page_path}",
        )
    try:
        probe_exclusive_flock(
            _sidecar_lock_path(page_path),
            unavailable_label="page lock",
        )
    finally:
        thread_lock.release()


@contextmanager
def page_rmw_lock(page_path: str | Path) -> Iterator[None]:
    """Hold an exclusive lock for one file's full RMW lifecycle (thread- and process-safe)."""
    key = normalize_page_lock_key(page_path)
    thread_lock = _lock_for_key(key)
    delay = IO_RETRY_INITIAL_DELAY_S
    for attempt in range(IO_RETRY_ATTEMPTS):
        if thread_lock.acquire(blocking=False):
            break
        if attempt >= IO_RETRY_ATTEMPTS - 1:
            logger.warning(
                "In-process page lock still held after {} retries: {}",
                IO_RETRY_ATTEMPTS - 1,
                page_path,
            )
            raise PageLockUnavailableError(
                f"Could not acquire in-process page lock for {page_path} after retries",
            )
        time.sleep(min(IO_RETRY_MAX_DELAY_S, delay))
        delay = min(IO_RETRY_MAX_DELAY_S, delay * 2)
    try:
        with _cross_process_file_lock(page_path):
            yield
    finally:
        thread_lock.release()


def clear_page_write_locks() -> None:
    """Drop the in-process lock registry (for tests)."""
    with _registry_guard:
        _page_locks.clear()


def sweep_matryca_lock_sidecars(graph_root: str | Path) -> int:
    """Remove orphan ``.{page}.matryca.lock`` sidecars under ``pages/`` and ``journals/``."""
    root = Path(graph_root).expanduser().resolve(strict=False)
    removed = 0
    for sub in ("pages", "journals"):
        base = root / sub
        if not base.is_dir():
            continue
        for candidate in base.rglob("*.matryca.lock"):
            if candidate.is_file():
                candidate.unlink(missing_ok=True)
                removed += 1
    return removed


def cross_process_lock_available() -> bool:
    """Return whether OS-level ``flock`` locking is active on this platform."""
    return _fcntl is not None and sys.platform != "win32"


__all__ = [
    "clear_page_write_locks",
    "cross_process_lock_available",
    "normalize_page_lock_key",
    "PageLockUnavailableError",
    "page_rmw_lock",
    "probe_page_rmw_lock",
    "sweep_matryca_lock_sidecars",
]
