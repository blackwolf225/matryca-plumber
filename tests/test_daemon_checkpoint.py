"""Tests for read-only daemon checkpoint access."""

from __future__ import annotations

from pathlib import Path

from src.agent.maintenance_daemon import DaemonState, save_daemon_state
from src.daemon.checkpoint import read_daemon_checkpoint


def test_read_daemon_checkpoint_reads_bootstrap_fields(tmp_path: Path) -> None:
    (tmp_path / "pages").mkdir()
    save_daemon_state(
        tmp_path,
        DaemonState(
            bootstrap_complete=False,
            bootstrap_scanned=4,
            bootstrap_total=9,
            bootstrap_failed=True,
            bootstrap_failed_reason="disk full",
            status="idle",
        ),
    )
    view = read_daemon_checkpoint(tmp_path)
    assert view.bootstrap_complete is False
    assert view.bootstrap_scanned == 4
    assert view.bootstrap_total == 9
    assert view.bootstrap_failed is True
    assert view.bootstrap_failed_reason == "disk full"
    assert view.status == "idle"


def test_read_daemon_checkpoint_empty_when_missing(tmp_path: Path) -> None:
    (tmp_path / "pages").mkdir()
    view = read_daemon_checkpoint(tmp_path)
    assert view.bootstrap_complete is False
    assert view.bootstrap_total == 0
