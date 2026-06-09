"""Optional NDJSON debug logging for local LLM JSON resilience investigations."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from loguru import logger

from .config_paths import resolve_optional_path_under_allowed_roots
from .json_repair import max_consecutive_literal_backslash_n
from .secret_redaction import redact_for_log


def _debug_enabled() -> bool:
    return os.environ.get("MATRYCA_LLM_DEBUG_JSON", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _debug_log_path() -> Path:
    custom = os.environ.get("MATRYCA_LLM_DEBUG_LOG_PATH", "").strip()
    if custom:
        allowed = resolve_optional_path_under_allowed_roots(custom)
        if allowed is not None:
            return allowed
        logger.warning(
            "MATRYCA_LLM_DEBUG_LOG_PATH is outside allowed roots; "
            "using default .cursor/debug-llm.jsonl",
        )
    return Path(__file__).resolve().parents[2] / ".cursor" / "debug-llm.jsonl"


def completion_usage_tokens(completion: object) -> dict[str, int]:
    usage = getattr(completion, "usage", None)
    if usage is None:
        return {}
    return {
        "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
        "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
    }


def agent_debug_log(
    *,
    location: str,
    message: str,
    data: dict[str, Any],
    hypothesis_id: str,
    run_id: str = "pre-fix",
) -> None:
    # #region agent log
    if not _debug_enabled():
        return
    try:
        payload = {
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        path = _debug_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        line = redact_for_log(json.dumps(payload, ensure_ascii=False)) + "\n"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line)
    except OSError:
        pass
    # #endregion


__all__ = [
    "agent_debug_log",
    "completion_usage_tokens",
    "max_consecutive_literal_backslash_n",
]
