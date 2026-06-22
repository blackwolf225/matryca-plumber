# Portions adapted from Nacre (https://github.com/marcusschimizzi/nacre)
# Copyright 2026 Marcus Sullivan
# SPDX-License-Identifier: Apache-2.0
# Modified by Marco Porcellato & Matryca.ai for Logseq OG integration.

"""Ebbinghaus decay math for the biological memory graph (Epic #99, Phase A).

Pure functions only — no I/O. Parity target: ``packages/core/src/decay.ts``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime

DEFAULT_DECAY_RATE = 0.015
DEFAULT_REINFORCEMENT_BOOST = 1.5
_MS_PER_DAY = 86_400_000


def days_between(date_a: str, date_b: str) -> int:
    """Return whole days between two ISO timestamps (absolute, floor).

    Matches Nacre elapsed-time semantics: sub-day gaps count as 0 days.
    """
    parsed_a = _parse_iso_datetime(date_a)
    parsed_b = _parse_iso_datetime(date_b)
    delta_ms = abs(int((parsed_b - parsed_a).total_seconds() * 1000))
    return delta_ms // _MS_PER_DAY


def calculate_stability(
    reinforcement_count: int,
    reinforcement_boost: float = DEFAULT_REINFORCEMENT_BOOST,
) -> float:
    """Return stability *S* — higher values resist decay (Nacre ``calculateStability``)."""
    return 1.0 + reinforcement_boost * math.log(reinforcement_count + 1)


def calculate_decayed_weight(
    base_weight: float,
    stability: float,
    elapsed_days: int,
    decay_rate: float = DEFAULT_DECAY_RATE,
) -> float:
    """Return decayed edge weight using the Ebbinghaus exponential.

    ``weight = base_weight × exp(-(λ × t) / S)`` clamped to ``>= 0``.
    """
    if stability <= 0.0:
        msg = "stability must be positive"
        raise ValueError(msg)
    if elapsed_days < 0:
        msg = "elapsed_days must be non-negative"
        raise ValueError(msg)
    if base_weight <= 0.0:
        return 0.0
    exponent = -(decay_rate * float(elapsed_days)) / stability
    return max(base_weight * math.exp(exponent), 0.0)


def half_life_days(
    stability: float,
    decay_rate: float = DEFAULT_DECAY_RATE,
) -> float:
    """Return continuous half-life in days for a given stability factor."""
    if stability <= 0.0:
        msg = "stability must be positive"
        raise ValueError(msg)
    return math.log(2.0) * stability / decay_rate


@dataclass(frozen=True, slots=True)
class MemoryEdgeState:
    """Minimal inputs to evaluate one memory edge's decayed weight."""

    base_weight: float
    reinforcement_count: int
    elapsed_days: int = 0
    decay_rate: float = DEFAULT_DECAY_RATE
    reinforcement_boost: float = DEFAULT_REINFORCEMENT_BOOST

    @property
    def stability(self) -> float:
        return calculate_stability(self.reinforcement_count, self.reinforcement_boost)

    def decayed_weight(self) -> float:
        """Return the current weight after ``elapsed_days`` without reinforcement."""
        return calculate_decayed_weight(
            self.base_weight,
            self.stability,
            self.elapsed_days,
            self.decay_rate,
        )


def compute_decayed_weight_from_dates(
    base_weight: float,
    reinforcement_count: int,
    last_reinforced: str,
    now_iso: str,
    *,
    decay_rate: float = DEFAULT_DECAY_RATE,
    reinforcement_boost: float = DEFAULT_REINFORCEMENT_BOOST,
) -> float:
    """Convenience wrapper mirroring Nacre ``computeCurrentWeight`` date inputs."""
    elapsed = days_between(last_reinforced, now_iso)
    stability = calculate_stability(reinforcement_count, reinforcement_boost)
    return calculate_decayed_weight(base_weight, stability, elapsed, decay_rate)


def _parse_iso_datetime(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


__all__ = [
    "DEFAULT_DECAY_RATE",
    "DEFAULT_REINFORCEMENT_BOOST",
    "MemoryEdgeState",
    "calculate_decayed_weight",
    "calculate_stability",
    "compute_decayed_weight_from_dates",
    "days_between",
    "half_life_days",
]
