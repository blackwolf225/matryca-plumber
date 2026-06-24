"""Shared cross-lingual constraints for Matryca Plumber LLM system prompts."""

from __future__ import annotations

from ..graph.prompt_constraints import (
    CROSS_LINGUAL_OUTPUT_CONSTRAINT,
    finalize_system_prompt,
)

ALIAS_FIRST_LINK_CONSTRAINT = (
    "Before suggesting any new topic link, you must verify if the concept already exists "
    "as a canonical page or an alias inside the AliasIndex. You must aggressively prefer "
    "linking to an existing canonical node or recommending an alias:: property over "
    "creating a new physical markdown file. New page files are an absolute last resort."
)

__all__ = [
    "ALIAS_FIRST_LINK_CONSTRAINT",
    "CROSS_LINGUAL_OUTPUT_CONSTRAINT",
    "finalize_system_prompt",
]
