"""Tests for the ``matryca-plumber`` console-script router."""

from __future__ import annotations

import sys

import pytest
from src.plumber_entry import _mcp_stdio_enabled, _normalize_cli_argv
from src.plumber_entry import main as plumber_entry_main


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        ([], None),
        (["status"], ["plumber", "status"]),
        (["start", "--foreground"], ["plumber", "start", "--foreground"]),
        (["plumber", "status"], ["plumber", "status"]),
        (["read", "page", "Home"], ["read", "page", "Home"]),
        (["--help"], ["--help"]),
        (["-h"], ["-h"]),
        (["unknown"], None),
    ],
)
def test_normalize_cli_argv(argv: list[str], expected: list[str] | None) -> None:
    assert _normalize_cli_argv(argv) == expected


def test_mcp_stdio_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MATRYCA_MCP_ENABLED", raising=False)
    assert _mcp_stdio_enabled() is False


def test_mcp_stdio_enabled_when_flag_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MATRYCA_MCP_ENABLED", "true")
    assert _mcp_stdio_enabled() is True


def test_plumber_entry_status_opens_ui_without_starting_daemon(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``uvx … matryca-plumber status`` must match ``matryca plumber status`` (UI only)."""
    ui_calls: list[bool] = []
    start_calls: list[bool] = []

    monkeypatch.setattr("src.cli.try_prepare_matryca_runtime_from_env", lambda: None)

    def _run_ui_server() -> None:
        ui_calls.append(True)

    monkeypatch.setattr("src.cli.run_ui_server", _run_ui_server)

    def _start_detached(*_args: object, **_kwargs: object) -> dict[str, bool]:
        start_calls.append(True)
        return {"ok": True}

    monkeypatch.setattr("src.cli.start_daemon_detached", _start_detached)
    monkeypatch.setattr(
        "src.cli.start_daemon_foreground",
        lambda *_args, **_kwargs: start_calls.append(True),
    )
    monkeypatch.setattr(sys, "argv", ["matryca-plumber", "status"])

    with pytest.raises(SystemExit) as exc:
        plumber_entry_main()

    assert exc.value.code == 0
    assert ui_calls == [True]
    assert start_calls == []
