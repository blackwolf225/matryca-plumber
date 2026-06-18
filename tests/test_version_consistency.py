"""Tests for release doc version consistency guard."""

from __future__ import annotations

from pathlib import Path

from scripts.check_version_consistency import check_llms_header, pyproject_version


def test_llms_headers_match_pyproject() -> None:
    root = Path(__file__).resolve().parents[1]
    version = pyproject_version()
    check_llms_header(root / "llms.txt", version)
    check_llms_header(root / ".well-known" / "llms.txt", version)
