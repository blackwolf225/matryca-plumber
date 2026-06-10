"""Tests for daemon journey log (#16)."""

from __future__ import annotations

from datetime import date

from src.agent.journey_log import (
    JourneyCycleStats,
    JourneyDayLedger,
    format_journey_activity_line,
)


def test_journey_activity_line_cumulative_format() -> None:
    ledger = JourneyDayLedger(day="2026-06-05", cycles=3)
    ledger.llm_files_processed = 2
    ledger.links_checked = 8
    ledger.dead_links_flagged = 1
    line = format_journey_activity_line(ledger)
    assert line.startswith("- 🤖 Matryca Activity —")
    assert "indexed 2 page(s)" in line
    assert "checked 8 link(s)" in line
    assert "flagged 1 block(s)" in line
    assert "3 duty cycle(s)" in line
    assert "## " not in line


def test_journey_day_ledger_accumulates_and_resets() -> None:
    ledger = JourneyDayLedger(day="2026-06-04")
    ledger.accumulate(
        JourneyCycleStats(llm_files_processed=1, links_checked=4, fast_track_files=1),
    )
    ledger.accumulate(
        JourneyCycleStats(llm_files_processed=2, links_checked=6, dead_links_flagged=1),
    )
    assert ledger.cycles == 2
    assert ledger.llm_files_processed == 3
    assert ledger.links_checked == 10
    assert ledger.fast_track_files == 1
    assert ledger.dead_links_flagged == 1

    ledger.reset_if_new_day(date(2026, 6, 5))
    assert ledger.day == "2026-06-05"
    assert ledger.cycles == 0
    assert ledger.llm_files_processed == 0


def test_journey_cycle_stats_has_journal_activity() -> None:
    assert not JourneyCycleStats().has_journal_activity()
    assert JourneyCycleStats(links_checked=1).has_journal_activity()
    assert JourneyCycleStats(llm_files_processed=1).has_journal_activity()


def test_journey_day_ledger_json_roundtrip() -> None:
    ledger = JourneyDayLedger(
        day="2026-06-05",
        cycles=5,
        llm_files_processed=3,
        links_checked=12,
    )
    restored = JourneyDayLedger.from_json(ledger.to_json())
    assert restored == ledger


def test_journey_day_ledger_from_json_tolerates_corrupt_fields() -> None:
    ledger = JourneyDayLedger.from_json(
        {"day": "2026-06-10", "cycles": "many", "links_checked": None}
    )
    assert ledger.day == "2026-06-10"
    assert ledger.cycles == 0
    assert ledger.links_checked == 0
