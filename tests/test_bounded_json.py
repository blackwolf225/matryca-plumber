"""Tests for bounded JSON checkpoint reads."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from src.utils.bounded_json import BoundedJsonError, read_bounded_json


def test_read_bounded_json_parses_valid_file(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    path.write_text(json.dumps({"ok": True}), encoding="utf-8")
    assert read_bounded_json(path) == {"ok": True}


def test_read_bounded_json_rejects_oversized_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "big.json"
    path.write_text("[" + "1," * 500 + "1]", encoding="utf-8")
    monkeypatch.setenv("MATRYCA_JSON_MAX_BYTES", "32")
    with pytest.raises(BoundedJsonError, match="exceeds"):
        read_bounded_json(path)


def test_read_bounded_json_caps_via_explicit_max_bytes(tmp_path: Path) -> None:
    path = tmp_path / "big.json"
    path.write_text(json.dumps(list(range(100))), encoding="utf-8")
    with pytest.raises(BoundedJsonError, match="exceeds"):
        read_bounded_json(path, max_bytes=16)
