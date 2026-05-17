"""Tests for Logseq template discovery."""

from __future__ import annotations

from pathlib import Path

import pytest
from src.graph.templates import list_logseq_templates, read_logseq_template


def test_list_and_read_template(tmp_path: Path) -> None:
    td = tmp_path / "templates"
    td.mkdir()
    (td / "daily.md").write_text("- type:: journal\n", encoding="utf-8")

    names = list_logseq_templates(tmp_path, subdir="templates")
    assert "daily.md" in names

    rel, body = read_logseq_template(tmp_path, "daily", subdir="templates")
    assert rel.startswith("templates/")
    assert "journal" in body


def test_read_template_rejects_path_traversal(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="plain filename"):
        read_logseq_template(tmp_path, "../evil.md")
