"""Prompt assembly contracts (Application layer) — domain builders import only this module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from ..prompt_constraints import ALIAS_FIRST_LINK_CONSTRAINT, finalize_system_prompt

__all__ = [
    "ALIAS_FIRST_LINK_CONSTRAINT",
    "PromptContext",
    "SystemPromptBuilder",
    "compile_tier1a_prompt",
    "compile_tier1b_prompt",
]


@dataclass(frozen=True, slots=True)
class PromptContext:
    """Variable knobs for system prompt assembly (stable across per-page KV prefix)."""

    output_language: str | None = None
    require_json: bool = False
    schema_name: str | None = None
    extra_constraints: tuple[str, ...] = ()


def _resolve_ctx(ctx: PromptContext | None) -> PromptContext:
    return PromptContext() if ctx is None else ctx


class SystemPromptBuilder(Protocol):
    """Contract for Tier-1 daemon system prompt builders."""

    tier: Literal["1A", "1B"]

    def build(self, ctx: PromptContext | None = None) -> str: ...


def compile_tier1a_prompt(
    *,
    role: str,
    invariants: tuple[str, ...],
    output: str,
    abort: str,
    ctx: PromptContext | None = None,
    alias_first: bool = False,
) -> str:
    """Assemble a Tier-1A compiler system prompt and append cross-lingual tail."""
    resolved = _resolve_ctx(ctx)
    sections = [
        role,
        "[INVARIANTS]",
        *invariants,
        "[OUTPUT]",
        output,
        "[ABORT]",
        abort,
    ]
    if alias_first:
        sections.append(ALIAS_FIRST_LINK_CONSTRAINT)
    for extra in resolved.extra_constraints:
        sections.append(extra)
    return finalize_system_prompt("\n".join(sections))


def compile_tier1b_prompt(
    *,
    role: str,
    goal: str,
    style: str,
    guardrails: str,
    ctx: PromptContext | None = None,
) -> str:
    """Assemble a Tier-1B writer system prompt and append cross-lingual tail."""
    resolved = _resolve_ctx(ctx)
    sections = [role, "[GOAL]", goal, "[STYLE]", style, "[GUARDRAILS]", guardrails]
    for extra in resolved.extra_constraints:
        sections.append(extra)
    return finalize_system_prompt("\n".join(sections))
