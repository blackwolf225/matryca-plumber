"""Bounded JSON reads for graph-local checkpoint files (memory DoS guard)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_DEFAULT_MAX_BYTES = 64_000_000
_MAX_BYTES_ENV = "MATRYCA_JSON_MAX_BYTES"


class BoundedJsonError(ValueError):
    """Raised when a JSON checkpoint exceeds the configured size cap."""


def json_max_bytes() -> int:
    raw = os.environ.get(_MAX_BYTES_ENV, "").strip()
    if not raw:
        return _DEFAULT_MAX_BYTES
    try:
        return max(1, int(raw))
    except ValueError:
        return _DEFAULT_MAX_BYTES


def read_bounded_json(
    path: Path | str,
    *,
    max_bytes: int | None = None,
    encoding: str = "utf-8",
) -> Any:
    """Read and parse JSON from ``path`` after enforcing a byte-size cap."""
    cap = max_bytes if max_bytes is not None else json_max_bytes()
    file_path = Path(path)
    try:
        with file_path.open("rb") as handle:
            data = handle.read(cap + 1)
    except OSError as exc:
        raise BoundedJsonError(f"Cannot read JSON checkpoint: {file_path}") from exc
    if len(data) > cap:
        raise BoundedJsonError(
            f"JSON checkpoint exceeds {cap} bytes: {file_path}",
        )
    try:
        text = data.decode(encoding)
    except UnicodeDecodeError as exc:
        raise BoundedJsonError(f"Cannot decode JSON checkpoint: {file_path}") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise BoundedJsonError(f"Invalid JSON in checkpoint: {file_path}") from exc


__all__ = [
    "BoundedJsonError",
    "json_max_bytes",
    "read_bounded_json",
]
