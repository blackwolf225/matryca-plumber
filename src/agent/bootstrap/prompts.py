"""Bootstrap harvest system prompts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..prompts.core import PromptContext, compile_tier1a_prompt


@dataclass(frozen=True, slots=True)
class HarvestPromptBuilder:
    """Tier-1A compiler prompt for Phase-1 catalog summaries."""

    tier: Literal["1A"] = "1A"

    def build(self, ctx: PromptContext | None = None) -> str:
        return compile_tier1a_prompt(
            role="You are Matryca Plumber's bootstrap harvester for Logseq OG.",
            invariants=(
                "Write one crisp sentence summarizing the page in the same language "
                "as the content.",
                "suggested_tags: 0-5 tags when clearly inferable.",
                "Optional MARPA domain only when clearly inferable: "
                "mappa|area|risorsa|progetto|archivio.",
            ),
            output=(
                "Return JSON only matching BootstrapSummaryResult. "
                "Fields: summary, suggested_tags, domain."
            ),
            abort=(
                "If the page body is empty or unreadable, return an empty summary "
                "and omit domain."
            ),
            ctx=ctx,
        )


def build_harvest_system_prompt() -> str:
    return HarvestPromptBuilder().build()


__all__ = ["HarvestPromptBuilder", "build_harvest_system_prompt"]
