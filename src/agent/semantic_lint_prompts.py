"""Stable system prompts for semantic lint / indexing (KV-cache friendly).

Deprecated import path — use ``src.agent.semantic_lint.prompts`` directly.
"""

from __future__ import annotations

from .semantic_lint.prompts import (
    SemanticLintPromptBuilder,
    build_semantic_lint_system_prompt,
)

__all__ = ["SemanticLintPromptBuilder", "build_semantic_lint_system_prompt"]
