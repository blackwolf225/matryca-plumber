"""Regression tests for daemon lock-backoff ledger behavior."""

from __future__ import annotations

from src.agent.maintenance_daemon import (
    DaemonState,
    FileState,
    _record_page_lock_backoff,
)


def test_record_page_lock_backoff_preserves_processed_status() -> None:
    state = DaemonState()
    key = "pages/Demo.md"
    prior = FileState(
        mtime=100.0,
        processed_at="2026-06-23T12:00:00+00:00",
        status="processed",
    )
    state.files[key] = prior
    _record_page_lock_backoff(
        state,
        key=key,
        mtime=100.0,
        message="page lock unavailable",
        prior=prior,
    )
    rec = state.files[key]
    assert rec.status == "processed"
    assert rec.processed_at == prior.processed_at
