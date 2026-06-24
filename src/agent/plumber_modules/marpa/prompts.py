"""MARPA classification system prompts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ...prompts.core import PromptContext, compile_tier1a_prompt


@dataclass(frozen=True, slots=True)
class MarpaClassifyPromptBuilder:
    """Tier-1A compiler prompt for MARPA domain classification."""

    tier: Literal["1A"] = "1A"

    def build(self, ctx: PromptContext | None = None) -> str:
        return compile_tier1a_prompt(
            role="You are the MARPA semantic taxonomy compiler for Logseq OG.",
            invariants=(
                "Assign exactly one domain from the user-provided catalog.",
                "Populate inferred_properties for missing structural fields "
                "(deadline, status, owner).",
                "Use standardized Logseq property keys; leave values empty when unknown.",
            ),
            output="Return JSON only matching MarpaClassificationResult.",
            abort=(
                "If the page content is blank, assign archivio only when clearly dormant; "
                "otherwise omit domain."
            ),
            ctx=ctx,
        )


def build_marpa_classify_system_prompt() -> str:
    return MarpaClassifyPromptBuilder().build()


__all__ = ["MarpaClassifyPromptBuilder", "build_marpa_classify_system_prompt"]
