"""Tests for require_explicit_ui_token_if_configured."""

from __future__ import annotations

import pytest
from src.cli.ui_auth import require_explicit_ui_token_if_configured


def test_require_explicit_token_raises_when_enabled_without_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MATRYCA_UI_REQUIRE_EXPLICIT_TOKEN", "true")
    monkeypatch.delenv("MATRYCA_UI_TOKEN", raising=False)
    with pytest.raises(ValueError, match="MATRYCA_UI_TOKEN"):
        require_explicit_ui_token_if_configured()


def test_require_explicit_token_allows_when_token_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MATRYCA_UI_REQUIRE_EXPLICIT_TOKEN", "true")
    monkeypatch.setenv("MATRYCA_UI_TOKEN", "fixed-token")
    require_explicit_ui_token_if_configured()
