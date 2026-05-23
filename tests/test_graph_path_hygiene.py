"""Cross-platform graph path hygiene (Windows separators, journal detection)."""

from __future__ import annotations

import sys
from pathlib import Path, PureWindowsPath

import pytest
from src.agent.plumber_modules._shared import is_journal_page_path


def test_is_journal_page_path_accepts_journal_tree(tmp_path: Path) -> None:
    journals = tmp_path / "journals"
    journals.mkdir()
    journal_file = journals / "2026_05_22.md"
    journal_file.write_text("- daily\n", encoding="utf-8")

    assert is_journal_page_path(tmp_path, journal_file) is True


def test_is_journal_page_path_rejects_pages_tree(tmp_path: Path) -> None:
    pages = tmp_path / "pages"
    pages.mkdir()
    page_file = pages / "Topic.md"
    page_file.write_text("- note\n", encoding="utf-8")

    assert is_journal_page_path(tmp_path, page_file) is False


def test_windows_journal_path_relative_parts_use_journals_segment() -> None:
    """Regression guard: use ``Path.parts``, not ``'journals/' in path`` string checks."""
    graph = PureWindowsPath(r"C:\graph")
    page = PureWindowsPath(r"C:\graph\journals\2026_05_22.md")
    assert page.relative_to(graph).parts == ("journals", "2026_05_22.md")


@pytest.mark.skipif(sys.platform != "win32", reason="Windows drive-letter paths")
def test_is_journal_page_path_accepts_windows_style_absolute_path(tmp_path: Path) -> None:
    """On Windows, ``C:\\graph\\journals\\2026.md`` must classify as a journal page."""
    graph_root = tmp_path.resolve()
    journal_file = graph_root / "journals" / "2026_05_22.md"
    journal_file.parent.mkdir(parents=True, exist_ok=True)
    journal_file.write_text("- daily\n", encoding="utf-8")

    page_path = Path(str(graph_root).replace("/", "\\")) / "journals" / "2026_05_22.md"
    assert is_journal_page_path(graph_root, page_path) is True
