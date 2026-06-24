"""Cache-aligned prompt layout for LM Studio / llama.cpp KV prefix reuse."""

from __future__ import annotations

from ..graph.prompt_layout import (
    CANONICAL_TASK_HEADER,
    build_cache_aligned_prompt,
    normalize_stable_text,
)

__all__ = [
    "CANONICAL_TASK_HEADER",
    "build_cache_aligned_prompt",
    "normalize_stable_text",
]
