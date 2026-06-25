"""LLM task system prompts for plumber cognitive modules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ...prompts.core import PromptContext, compile_tier1a_prompt


@dataclass(frozen=True, slots=True)
class ContextualSeedPromptBuilder:
    tier: Literal["1A"] = "1A"

    def build(self, ctx: PromptContext | None = None) -> str:
        return compile_tier1a_prompt(
            role="You seed new Logseq pages from local context.",
            invariants=(
                "Write a neutral, concise definition without markdown headings.",
                "Do not invent facts absent from the supplied context.",
            ),
            output="Return JSON only matching ContextualSeedResult.",
            abort="If context is insufficient, return a minimal neutral stub definition.",
            ctx=ctx,
        )


@dataclass(frozen=True, slots=True)
class EntityOverlapPromptBuilder:
    tier: Literal["1A"] = "1A"

    def build(self, ctx: PromptContext | None = None) -> str:
        return compile_tier1a_prompt(
            role="You are an entity consolidation linter for Logseq.",
            invariants=(
                "Prefer one canonical title and register the other as alias.",
                "Never suggest merging file contents or deleting pages.",
            ),
            output="Return JSON only matching EntityOverlapResult.",
            abort="If overlap is unclear, prefer keeping titles separate.",
            ctx=ctx,
        )


@dataclass(frozen=True, slots=True)
class TagPropertiesPromptBuilder:
    tier: Literal["1A"] = "1A"

    def build(self, ctx: PromptContext | None = None) -> str:
        return compile_tier1a_prompt(
            role="You infer Logseq block properties from page context.",
            invariants=(
                "Use empty string for unknown property values.",
                "Only emit keys requested in the task instruction.",
            ),
            output="Return JSON only matching InferredPropertiesResult with a properties object.",
            abort="If a key cannot be inferred, set it to an empty string.",
            ctx=ctx,
        )


def build_contextual_seed_system_prompt() -> str:
    return ContextualSeedPromptBuilder().build()


def build_entity_overlap_system_prompt() -> str:
    return EntityOverlapPromptBuilder().build()


def build_tag_properties_system_prompt() -> str:
    return TagPropertiesPromptBuilder().build()


__all__ = [
    "ContextualSeedPromptBuilder",
    "EntityOverlapPromptBuilder",
    "TagPropertiesPromptBuilder",
    "build_contextual_seed_system_prompt",
    "build_entity_overlap_system_prompt",
    "build_tag_properties_system_prompt",
]
