"""Cache-aligned prompt layout for LM Studio / llama.cpp KV prefix reuse."""

from __future__ import annotations

_CONTENT_HEADER = "Page content:\n"


def build_cache_aligned_prompt(*, content: str, task_instruction: str) -> str:
    """Place stable page content first and dynamic task instructions last.

    Layout: ``[FILE_CONTENT] + [DYNAMIC_TASK_INSTRUCTION]`` so consecutive LLM
    turns on the same file share the heaviest token prefix for prompt caching.
    """
    body = content.strip()
    task = task_instruction.strip()
    if not body:
        return task
    if not task:
        return f"{_CONTENT_HEADER}{body}"
    return f"{_CONTENT_HEADER}{body}\n\n{task}"


__all__ = ["build_cache_aligned_prompt"]
