"""Numerical parity tests for Nacre Ebbinghaus decay (Epic #99, Phase A)."""

from __future__ import annotations

import math

import pytest
from src.memory.decay import (
    DEFAULT_DECAY_RATE,
    DEFAULT_REINFORCEMENT_BOOST,
    MemoryEdgeState,
    calculate_decayed_weight,
    calculate_stability,
    compute_decayed_weight_from_dates,
    days_between,
    half_life_days,
)

_EPSILON = 0.05


class TestDaysBetween:
    def test_same_date_is_zero(self) -> None:
        assert days_between("2026-01-15", "2026-01-15") == 0

    def test_different_dates(self) -> None:
        assert days_between("2026-01-10", "2026-01-15") == 5

    def test_commutative(self) -> None:
        assert days_between("2026-01-10", "2026-01-20") == days_between(
            "2026-01-20",
            "2026-01-10",
        )

    def test_cross_month(self) -> None:
        assert days_between("2026-01-30", "2026-02-02") == 3

    def test_sub_day_difference_is_zero(self) -> None:
        assert days_between("2026-02-07T23:59:00", "2026-02-08T00:01:00") == 0


class TestCalculateStability:
    @pytest.mark.parametrize(
        ("reinforcement_count", "expected"),
        [
            (0, 1.0),
            (1, 2.04),
            (3, 3.08),
            (7, 4.12),
            (15, 5.16),
            (30, 6.15),
        ],
    )
    def test_nacre_reference_values(
        self,
        reinforcement_count: int,
        expected: float,
    ) -> None:
        stability = calculate_stability(reinforcement_count, DEFAULT_REINFORCEMENT_BOOST)
        assert abs(stability - expected) < _EPSILON

    def test_monotonic_with_reinforcement(self) -> None:
        previous = 0.0
        for count in range(31):
            stability = calculate_stability(count, DEFAULT_REINFORCEMENT_BOOST)
            assert stability > previous
            previous = stability


class TestCalculateDecayedWeight:
    def test_zero_elapsed_returns_base_weight(self) -> None:
        weight = calculate_decayed_weight(1.0, 1.0, 0)
        assert abs(weight - 1.0) < 0.01

    def test_never_negative(self) -> None:
        weight = calculate_decayed_weight(1.0, 1.0, 10_000)
        assert weight >= 0.0

    def test_zero_base_weight(self) -> None:
        assert calculate_decayed_weight(0.0, 1.0, 100) == 0.0

    def test_invalid_stability_raises(self) -> None:
        with pytest.raises(ValueError, match="stability"):
            calculate_decayed_weight(1.0, 0.0, 1)

    def test_negative_elapsed_raises(self) -> None:
        with pytest.raises(ValueError, match="elapsed_days"):
            calculate_decayed_weight(1.0, 1.0, -1)


class TestNacreComputeCurrentWeightParity:
    """Mirrors ``packages/core/src/__tests__/decay.test.ts`` computeCurrentWeight block."""

    def test_t_zero_returns_base_weight(self) -> None:
        weight = compute_decayed_weight_from_dates(
            1.0,
            0,
            "2026-01-15T00:00:00.000Z",
            "2026-01-15T00:00:00.000Z",
        )
        assert abs(weight - 1.0) < 0.01

    def test_half_life_46_days_for_r0(self) -> None:
        weight = compute_decayed_weight_from_dates(
            1.0,
            0,
            "2026-01-01T00:00:00.000Z",
            "2026-02-16T00:00:00.000Z",
        )
        assert abs(weight - 0.5) < 0.05

    def test_higher_reinforcement_decays_slower(self) -> None:
        now = "2026-03-01T00:00:00.000Z"
        last = "2026-01-01T00:00:00.000Z"
        weight_r0 = compute_decayed_weight_from_dates(1.0, 0, last, now)
        weight_r7 = compute_decayed_weight_from_dates(1.0, 7, last, now)
        assert weight_r7 > weight_r0


class TestHalfLifeTable:
    """Nacre ARCHITECTURE.md half-life table — continuous math, table days rounded."""

    @pytest.mark.parametrize(
        ("reinforcement_count", "table_half_life_days"),
        [
            (0, 46),
            (1, 92),
            (3, 143),
            (7, 189),
            (15, 240),
            (30, 281),
        ],
    )
    def test_weight_halves_near_documented_half_life(
        self,
        reinforcement_count: int,
        table_half_life_days: int,
    ) -> None:
        stability = calculate_stability(reinforcement_count, DEFAULT_REINFORCEMENT_BOOST)
        continuous_half_life = half_life_days(stability, DEFAULT_DECAY_RATE)
        # ARCHITECTURE.md rounds stability (e.g. R=30 → S=6.1 vs 6.15); allow slack.
        assert abs(continuous_half_life - table_half_life_days) <= 4.0

        weight_at_table_day = calculate_decayed_weight(
            1.0,
            stability,
            table_half_life_days,
        )
        assert abs(weight_at_table_day - 0.5) < 0.06

    def test_exact_continuous_half_life_is_precise(self) -> None:
        stability = calculate_stability(0, DEFAULT_REINFORCEMENT_BOOST)
        elapsed = int(round(half_life_days(stability)))
        weight = calculate_decayed_weight(1.0, stability, elapsed)
        assert abs(weight - 0.5) < 0.02


class TestMemoryEdgeState:
    def test_dataclass_matches_pure_functions(self) -> None:
        state = MemoryEdgeState(
            base_weight=1.0,
            reinforcement_count=7,
            elapsed_days=59,
        )
        expected = calculate_decayed_weight(
            1.0,
            calculate_stability(7, DEFAULT_REINFORCEMENT_BOOST),
            59,
        )
        assert state.decayed_weight() == expected

    def test_stability_property(self) -> None:
        state = MemoryEdgeState(base_weight=0.8, reinforcement_count=3)
        assert state.stability == calculate_stability(3, DEFAULT_REINFORCEMENT_BOOST)


def test_exponential_formula_identity() -> None:
    """Sanity: weight = W0 * exp(-λt/S) at t = S*ln(2)/λ yields W0/2."""
    stability = 2.5
    elapsed = int(math.floor(half_life_days(stability)))
    weight = calculate_decayed_weight(2.0, stability, elapsed)
    assert abs(weight - 1.0) < 0.03
