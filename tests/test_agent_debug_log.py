"""Tests for LLM debug log path allowlist and secret redaction."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from src.utils import agent_debug_log


def test_debug_log_path_rejects_outside_allowed_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MATRYCA_LLM_DEBUG_LOG_PATH", "/etc/passwd")
    path = agent_debug_log._debug_log_path()
    assert path.name == "debug-llm.jsonl"
    assert ".cursor" in path.as_posix()


def test_agent_debug_log_redacts_secrets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log_path = tmp_path / "debug.jsonl"
    monkeypatch.setenv("MATRYCA_LLM_DEBUG_JSON", "true")
    monkeypatch.setenv("MATRYCA_LLM_DEBUG_LOG_PATH", str(log_path))
    secret = "sk-abcdefghijklmnopqrstuvwxyz1234567890"
    agent_debug_log.agent_debug_log(
        location="test",
        message="probe",
        data={"prompt": secret},
        hypothesis_id="H1",
    )
    line = log_path.read_text(encoding="utf-8").strip()
    payload = json.loads(line)
    assert secret not in line
    assert "sk-" not in str(payload.get("data", {}))
