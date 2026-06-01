"""Journey Log: append daemon duty-cycle summaries to today's journal (#16)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date

from ..graph.journal_task_scan import append_journal_markdown_section


def journey_log_enabled() -> bool:
    raw = os.environ.get("MATRYCA_JOURNEY_LOG_ENABLED", "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


@dataclass
class JourneyCycleStats:
    """Aggregated metrics for one maintenance duty cycle."""

    llm_files_processed: int = 0
    links_checked: int = 0
    dead_links_flagged: int = 0
    missing_assets_flagged: int = 0
    fast_track_files: int = 0
    notes: list[str] = field(default_factory=list)

    def summary_lines(self) -> list[str]:
        lines = ["## 🤖 Matryca Activity"]
        parts: list[str] = []
        if self.llm_files_processed:
            parts.append(f"indexed {self.llm_files_processed} page(s)")
        if self.links_checked:
            parts.append(f"checked {self.links_checked} link(s)")
        flagged = self.dead_links_flagged + self.missing_assets_flagged
        if flagged:
            parts.append(f"flagged {flagged} block(s) (dead links / missing assets)")
        if self.fast_track_files:
            parts.append(f"fast-tracked {self.fast_track_files} file(s)")
        if not parts:
            parts.append("idle scan (no graph mutations)")
        lines.append(f"- {'; '.join(parts)}.")
        for note in self.notes:
            lines.append(f"- {note}")
        return lines


def format_journey_markdown(stats: JourneyCycleStats) -> str:
    return "\n".join(stats.summary_lines()) + "\n"


def append_journey_log(
    graph_root: str,
    stats: JourneyCycleStats,
    *,
    as_of: date | None = None,
) -> dict[str, object]:
    """Append the cycle summary under today's journal (non-dry-run)."""
    if not journey_log_enabled():
        return {"ok": True, "code": "disabled", "hint": "MATRYCA_JOURNEY_LOG_ENABLED is off"}
    body = format_journey_markdown(stats)
    return append_journal_markdown_section(graph_root, body, as_of=as_of, dry_run=False)


__all__ = [
    "JourneyCycleStats",
    "append_journey_log",
    "format_journey_markdown",
    "journey_log_enabled",
]
