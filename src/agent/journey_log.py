"""Journey Log: upsert a single cumulative activity bullet in today's journal (#16)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date

from ..graph.journal_task_scan import upsert_matryca_activity_block

MATRYCA_ACTIVITY_PREFIX = "🤖 Matryca Activity"


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

    def has_journal_activity(self) -> bool:
        """Return whether this cycle produced metrics worth writing to the journal."""
        flagged = self.dead_links_flagged + self.missing_assets_flagged
        return (
            self.llm_files_processed > 0
            or self.fast_track_files > 0
            or flagged > 0
            or self.links_checked > 0
        )


@dataclass
class JourneyDayLedger:
    """Cumulative journey metrics for one calendar day (daemon state source of truth)."""

    day: str = ""
    cycles: int = 0
    llm_files_processed: int = 0
    links_checked: int = 0
    dead_links_flagged: int = 0
    missing_assets_flagged: int = 0
    fast_track_files: int = 0

    def reset_if_new_day(self, today: date) -> None:
        iso = today.isoformat()
        if self.day != iso:
            self.day = iso
            self.cycles = 0
            self.llm_files_processed = 0
            self.links_checked = 0
            self.dead_links_flagged = 0
            self.missing_assets_flagged = 0
            self.fast_track_files = 0

    def accumulate(self, stats: JourneyCycleStats) -> None:
        self.cycles += 1
        self.llm_files_processed += stats.llm_files_processed
        self.links_checked += stats.links_checked
        self.dead_links_flagged += stats.dead_links_flagged
        self.missing_assets_flagged += stats.missing_assets_flagged
        self.fast_track_files += stats.fast_track_files

    def format_activity_line(self) -> str:
        parts: list[str] = []
        if self.llm_files_processed:
            parts.append(f"indexed {self.llm_files_processed} page(s)")
        if self.links_checked:
            parts.append(f"checked {self.links_checked} link(s)")
        flagged = self.dead_links_flagged + self.missing_assets_flagged
        if flagged:
            parts.append(f"flagged {flagged} block(s)")
        if self.fast_track_files:
            parts.append(f"fast-tracked {self.fast_track_files} file(s)")
        if self.cycles:
            parts.append(f"{self.cycles} duty cycle(s)")
        summary = "; ".join(parts) if parts else "no activity yet"
        return f"- {MATRYCA_ACTIVITY_PREFIX} — {summary}"

    def to_json(self) -> dict[str, object]:
        return {
            "day": self.day,
            "cycles": self.cycles,
            "llm_files_processed": self.llm_files_processed,
            "links_checked": self.links_checked,
            "dead_links_flagged": self.dead_links_flagged,
            "missing_assets_flagged": self.missing_assets_flagged,
            "fast_track_files": self.fast_track_files,
        }

    @classmethod
    def from_json(cls, payload: object) -> JourneyDayLedger:
        if not isinstance(payload, dict):
            return cls()
        return cls(
            day=str(payload.get("day", "")),
            cycles=int(payload.get("cycles", 0)),
            llm_files_processed=int(payload.get("llm_files_processed", 0)),
            links_checked=int(payload.get("links_checked", 0)),
            dead_links_flagged=int(payload.get("dead_links_flagged", 0)),
            missing_assets_flagged=int(payload.get("missing_assets_flagged", 0)),
            fast_track_files=int(payload.get("fast_track_files", 0)),
        )


def format_journey_activity_line(ledger: JourneyDayLedger) -> str:
    return ledger.format_activity_line() + "\n"


def upsert_journey_log(
    graph_root: str,
    ledger: JourneyDayLedger,
    *,
    as_of: date | None = None,
    dry_run: bool = False,
) -> dict[str, object]:
    """Upsert the cumulative activity bullet under today's journal."""
    if not journey_log_enabled():
        return {"ok": True, "code": "disabled", "hint": "MATRYCA_JOURNEY_LOG_ENABLED is off"}
    line = ledger.format_activity_line()
    return upsert_matryca_activity_block(graph_root, line, as_of=as_of, dry_run=dry_run)


__all__ = [
    "JourneyCycleStats",
    "JourneyDayLedger",
    "MATRYCA_ACTIVITY_PREFIX",
    "format_journey_activity_line",
    "journey_log_enabled",
    "upsert_journey_log",
]
