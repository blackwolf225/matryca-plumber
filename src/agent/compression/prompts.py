"""Context compression system prompts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..prompts.core import PromptContext, compile_tier1b_prompt


@dataclass(frozen=True, slots=True)
class CompressionPromptBuilder:
    """Tier-1B writer prompt for epistemic session condensation."""

    tier: Literal["1B"] = "1B"

    def build(self, ctx: PromptContext | None = None) -> str:
        return compile_tier1b_prompt(
            role="You are Matryca Plumber Context Compressor.",
            goal=(
                "Condense maintenance-session history into dense markdown titled "
                "'## Consolidated Epistemic State'."
            ),
            style=(
                "Use bullet lists and short headings. Preserve page titles processed, "
                "MARPA domains assigned, lint corrections applied, entity merges, dangling "
                "links healed, block UUIDs referenced, errors/skips, and open tasks. "
                "Omit filler."
            ),
            guardrails="Output markdown only. Do not prescribe destructive graph edits.",
            ctx=ctx,
        )


def build_compression_system_prompt() -> str:
    return CompressionPromptBuilder().build()


__all__ = ["CompressionPromptBuilder", "build_compression_system_prompt"]
