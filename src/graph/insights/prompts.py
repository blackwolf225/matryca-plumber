"""Graph Insights system prompts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ...agent.prompts.core import PromptContext, compile_tier1a_prompt

_JSON_TAIL = (
    "NEVER GENERATE NESTED UNESCAPED QUOTES OR TRAILING GARBAGE CONTEXT. "
    "TERMINATE THE JSON BLOCK CLEANLY IMMEDIATELY AFTER THE CLOSING OBJECT BRACKET. "
    "Return valid JSON only — no markdown fences, no prose after the closing brace."
)


@dataclass(frozen=True, slots=True)
class InsightsPromptBuilder:
    """Tier-1A compiler prompt for GraphInsightsLLMResult (prose lives inside JSON fields)."""

    tier: Literal["1A"] = "1A"

    def build(self, ctx: PromptContext | None = None) -> str:
        resolved = PromptContext() if ctx is None else ctx
        extra = (_JSON_TAIL, *resolved.extra_constraints)
        merged_ctx = PromptContext(
            output_language=resolved.output_language,
            require_json=True,
            schema_name="GraphInsightsLLMResult",
            extra_constraints=extra,
        )
        return compile_tier1a_prompt(
            role="You are Matryca Plumber's Graph Insights Engine for Logseq OG.",
            invariants=(
                "Analyze structural topology metrics for a personal knowledge graph.",
                "Surface hidden conceptual clusters, naming drift, and structural debt.",
                "Cleanup suggestions must be non-destructive short actionable sentences.",
                "Human-readable report fields must match the language of metric labels "
                "when localized.",
            ),
            output=(
                "Return JSON only matching GraphInsightsLLMResult. "
                "Populate ontology_report and cleanup_suggestions as structured fields."
            ),
            abort=(
                "If metrics JSON is empty, return an empty ontology_report and no "
                "cleanup suggestions."
            ),
            ctx=merged_ctx,
        )


def build_insights_system_prompt() -> str:
    return InsightsPromptBuilder().build()


__all__ = ["InsightsPromptBuilder", "build_insights_system_prompt"]
