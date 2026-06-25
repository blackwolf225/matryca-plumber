"""Tests for scripts/build_system_prompt.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_build_system_prompt_check_exits_zero() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_system_prompt.py"), "--check"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_unlisted_agent_fragment_fails_check(tmp_path: Path) -> None:
    from scripts.build_system_prompt import assert_no_unlisted_fragments

    agent_dir = tmp_path / "agent"
    agent_dir.mkdir()
    order_file = agent_dir / "_assembly_order.txt"
    order_file.write_text("listed.md\n", encoding="utf-8")
    (agent_dir / "listed.md").write_text("# Listed\n", encoding="utf-8")
    (agent_dir / "orphan.md").write_text("# Orphan\n", encoding="utf-8")

    with pytest.raises(SystemExit, match="orphan.md"):
        assert_no_unlisted_fragments(agent_dir=agent_dir, order_file=order_file)
