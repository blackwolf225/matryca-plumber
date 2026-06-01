"""Tests for daemon journey log (#16)."""

from __future__ import annotations

from src.agent.journey_log import JourneyCycleStats, format_journey_markdown


def test_journey_markdown_includes_activity_heading() -> None:
    stats = JourneyCycleStats(
        llm_files_processed=2,
        links_checked=5,
        dead_links_flagged=1,
    )
    md = format_journey_markdown(stats)
    assert "## 🤖 Matryca Activity" in md
    assert "indexed 2 page(s)" in md
    assert "checked 5 link(s)" in md
