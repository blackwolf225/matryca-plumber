"""Cooperative CPU/disk yielding so long graph scans stay host-responsive."""

from __future__ import annotations

from ..graph.cooperative_yield import (
    bootstrap_yield_every,
    io_batch_pause_seconds,
    yield_host,
    yield_sleep_seconds,
)
from ..utils.env_parse import env_float, env_int

_DEFAULT_TELEMETRY_HEARTBEAT_SECONDS = 5.0
_DEFAULT_BOOTSTRAP_CHECKPOINT_EVERY = 50
_DEFAULT_BOOTSTRAP_PILL_CHECKPOINT_EVERY = 5


def bootstrap_checkpoint_every() -> int:
    return max(
        1,
        env_int("MATRYCA_BOOTSTRAP_CHECKPOINT_EVERY", _DEFAULT_BOOTSTRAP_CHECKPOINT_EVERY),
    )


def bootstrap_pill_checkpoint_every() -> int:
    """How often Phase 1 pill history (``bootstrap_recent``) is flushed to disk."""
    return max(
        1,
        env_int(
            "MATRYCA_BOOTSTRAP_PILL_CHECKPOINT_EVERY",
            _DEFAULT_BOOTSTRAP_PILL_CHECKPOINT_EVERY,
        ),
    )


def telemetry_heartbeat_seconds() -> float:
    """Minimum interval between cooperative daemon telemetry checkpoints."""
    return max(
        1.0,
        env_float("MATRYCA_TELEMETRY_HEARTBEAT_SECONDS", _DEFAULT_TELEMETRY_HEARTBEAT_SECONDS),
    )


__all__ = [
    "bootstrap_checkpoint_every",
    "bootstrap_pill_checkpoint_every",
    "bootstrap_yield_every",
    "io_batch_pause_seconds",
    "telemetry_heartbeat_seconds",
    "yield_host",
    "yield_sleep_seconds",
]
