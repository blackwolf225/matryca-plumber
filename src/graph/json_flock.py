"""Cross-process exclusive flock for JSON checkpoint files."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from ..utils.platform_lock import cross_process_sidecar_lock


def flock_sidecar_path(target: Path) -> Path:
    """Return a sidecar lock path adjacent to ``target``."""
    return target.parent / f".{target.name}.flock"


@contextmanager
def cross_process_json_flock(target: Path) -> Iterator[None]:
    """Hold an exclusive flock for one JSON read/write critical section."""
    lock_path = flock_sidecar_path(target)
    depth_key = str(lock_path.expanduser().resolve(strict=False))
    with cross_process_sidecar_lock(
        lock_path,
        depth_key=depth_key,
        unavailable_label="JSON sidecar lock",
    ):
        yield


__all__ = ["cross_process_json_flock", "flock_sidecar_path"]
