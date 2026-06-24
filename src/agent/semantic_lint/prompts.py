"""Semantic lint / index system prompts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..prompts.core import PromptContext, compile_tier1a_prompt

_SEMANTIC_LINT_INVARIANTS = (
    "(1) block_uuid must match an id:: line from the page;",
    "(2) original_text must copy the bullet-line text verbatim "
    "(exclude id:: / property lines);",
    "(3) corrected_text must preserve original_text unchanged "
    "and only add [[WikiLinks]] or #tags;",
    "(4) never delete, shorten, or paraphrase user prose;",
    "(5) if unsure, omit the correction.",
    "(6) never propose edits inside fenced code (```), HTML comments, "
    "or #+BEGIN_QUERY … #+END_QUERY regions.",
)

_SEMANTIC_LINT_OUTPUT = (
    "Return JSON only matching SemanticLintResult. "
    "Fields: semantic_corrections, summary, cross_references, suggested_tags, moc_pointers. "
    "lint_type auto_wikilink: wrap recognizable concepts in [[Page Title]] links. "
    "lint_type tag_hygiene: normalize inline #tags without removing words. "
    "lint_type anomaly_warning: flag issues only — set corrected_text equal to original_text. "
    "Resolve wikilinks using the AliasIndex section in the user message when present."
)

_SEMANTIC_LINT_ABORT = (
    "If block_uuid is absent from the page catalog, omit that semantic_correction entirely."
)


@dataclass(frozen=True, slots=True)
class SemanticLintPromptBuilder:
    """Tier-1A compiler prompt for semantic lint and indexing."""

    tier: Literal["1A"] = "1A"

    def build(self, ctx: PromptContext | None = None) -> str:
        return compile_tier1a_prompt(
            role=(
                "You are Matryca Plumber, a semantic linter and indexer for Logseq OG "
                "outliner pages. Behave like a strict compiler: analyze block-by-block, "
                "propose only safe additive micro-corrections, never rewrite whole files."
            ),
            invariants=_SEMANTIC_LINT_INVARIANTS,
            output=_SEMANTIC_LINT_OUTPUT,
            abort=_SEMANTIC_LINT_ABORT,
            ctx=ctx,
            alias_first=True,
        )


_DEFAULT_BUILDER = SemanticLintPromptBuilder()


def build_semantic_lint_system_prompt() -> str:
    """Stable system prompt (alias map lives in the per-page user block for KV reuse)."""
    return _DEFAULT_BUILDER.build()


__all__ = ["SemanticLintPromptBuilder", "build_semantic_lint_system_prompt"]
