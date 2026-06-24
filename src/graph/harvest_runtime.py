"""Bootstrap harvest runtime knobs (MapReduce thresholds + thermal pause)."""

from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass

from ..utils.env_parse import env_float, env_int

_DEFAULT_THERMAL_DELAY_BOOTSTRAP = 2.0
_DEFAULT_MAPREDUCE_TRIGGER_CHARS = 25_000
_DEFAULT_MAPREDUCE_CHUNK_CHARS = 15_000


def _safe_thermal_seconds(seconds: float) -> float:
    try:
        value = float(seconds)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(value):
        return 0.0
    return max(0.0, value)


def _safe_nonneg_int(value: int, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, parsed)


@dataclass(frozen=True, slots=True)
class HarvestRuntimeConfig:
    """Graph-local harvest settings (no agent imports)."""

    thermal_delay_bootstrap: float = _DEFAULT_THERMAL_DELAY_BOOTSTRAP
    mapreduce_trigger_chars: int = _DEFAULT_MAPREDUCE_TRIGGER_CHARS
    mapreduce_chunk_chars: int = _DEFAULT_MAPREDUCE_CHUNK_CHARS


def load_harvest_runtime_config() -> HarvestRuntimeConfig:
    """Load harvest thresholds from the same env keys as ``PlumberLintConfig``."""
    return HarvestRuntimeConfig(
        thermal_delay_bootstrap=env_float(
            "MATRYCA_THERMAL_DELAY_BOOTSTRAP",
            _DEFAULT_THERMAL_DELAY_BOOTSTRAP,
        ),
        mapreduce_trigger_chars=_safe_nonneg_int(
            env_int("MATRYCA_PLUMBER_MAPREDUCE_TRIGGER_CHARS", _DEFAULT_MAPREDUCE_TRIGGER_CHARS),
            default=_DEFAULT_MAPREDUCE_TRIGGER_CHARS,
        ),
        mapreduce_chunk_chars=_safe_nonneg_int(
            env_int("MATRYCA_PLUMBER_MAPREDUCE_CHUNK_CHARS", _DEFAULT_MAPREDUCE_CHUNK_CHARS),
            default=_DEFAULT_MAPREDUCE_CHUNK_CHARS,
        ),
    )


def apply_thermal_pause_harvest(
    config: HarvestRuntimeConfig | None = None,
    *,
    stop_event: threading.Event | None = None,
) -> None:
    """GPU cool-down after one bootstrap harvest LLM turn (live env when config omitted)."""
    _ = config
    delay = _safe_thermal_seconds(load_harvest_runtime_config().thermal_delay_bootstrap)
    if delay <= 0:
        return
    if stop_event is None:
        time.sleep(delay)
        return
    stop_event.wait(timeout=delay)


__all__ = [
    "HarvestRuntimeConfig",
    "apply_thermal_pause_harvest",
    "load_harvest_runtime_config",
]
