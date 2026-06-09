"""Smoke test for sandbox read_text CI guard."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_sandbox_read_check_passes_on_clean_tree() -> None:
    repo = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(repo / "scripts" / "check_graph_read_sandbox.py")],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
