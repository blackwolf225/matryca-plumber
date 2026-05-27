"""Tests for ``.env.example`` template path detection."""

from __future__ import annotations

from src.utils.env_placeholders import is_template_env_path, normalize_env_path_value


def test_is_template_env_path_detects_example_values() -> None:
    assert is_template_env_path("/absolute/path/to/matryca-l1")
    assert is_template_env_path('"/absolute/path/to/your/Logseq/graph"')
    assert is_template_env_path("/path/to/your/custom/dir")


def test_is_template_env_path_allows_real_paths() -> None:
    assert not is_template_env_path("/Users/me/vault/matryca-l1")
    assert not is_template_env_path("")
    assert not is_template_env_path(None)


def test_normalize_env_path_value_strips_quotes() -> None:
    assert normalize_env_path_value('"/tmp/foo"') == "/tmp/foo"
