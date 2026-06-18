"""Pytest hooks: ensure ``logseq-matryca-parser`` is importable in dev."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

try:
    from logseq_matryca_parser import LogosParser  # noqa: F401
except ImportError:
    _PARSER_SRC = Path(__file__).resolve().parents[2] / "logseq-matryca-parser" / "src"
    if _PARSER_SRC.is_dir():
        parser_src = str(_PARSER_SRC)
        if parser_src not in sys.path:
            sys.path.insert(0, parser_src)
    from logseq_matryca_parser import LogosParser  # noqa: F401

_THERMAL_DELAY_ENV_KEYS = (
    "MATRYCA_THERMAL_DELAY_BOOTSTRAP",
    "MATRYCA_THERMAL_DELAY_COGNITIVE",
)


@pytest.fixture(autouse=True)
def zero_thermal_delays_in_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """Skip real thermal cool-down sleeps unless a test overrides these env vars."""
    for key in _THERMAL_DELAY_ENV_KEYS:
        monkeypatch.setenv(key, "0")
