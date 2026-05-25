"""Tests for the ``matryca-plumber`` console-script router."""

from __future__ import annotations

import pytest
from src.plumber_entry import _mcp_stdio_enabled, _normalize_cli_argv


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
