"""Synthesize applicability profiles for dual-vector retrieval."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..agent.llm_client import call_openai_with_transport_retries
from ..agent.plumber_config import resolve_llm_max_compression_tokens
from ..utils.json_repair import sanitize_prose_llm_completion

_APPLICABILITY_SYSTEM = (
    "You describe when a knowledge block is useful. Reply with one concise sentence only."
)

_APPLICABILITY_USER_TEMPLATE = (
    "Analyze this markdown block. In a single concise sentence, describe the exact user "
    "intent, scenario, or question where retrieving this information would be highly valuable.\n\n"
    "Block:\n{block_text}"
)


@runtime_checkable
class ApplicabilityLLM(Protocol):
    """Minimal LLM surface for applicability synthesis."""

    def complete_applicability(self, block_text: str) -> str: ...


def build_applicability_prompt(block_text: str) -> str:
    return _APPLICABILITY_USER_TEMPLATE.format(block_text=block_text.strip())


def synthesize_applicability(block_text: str, llm_client: ApplicabilityLLM) -> str:
    """Return a one-sentence applicability profile for ``block_text``."""
    cleaned = block_text.strip()
    if not cleaned:
        msg = "block_text must be non-empty"
        raise ValueError(msg)
    sentence = llm_client.complete_applicability(cleaned).strip()
    if not sentence:
        msg = "applicability LLM returned empty text"
        raise ValueError(msg)
    return sentence


class InstructorApplicabilityLLM:
    """Adapter around ``InstructorLLMClient`` for applicability prose."""

    def __init__(self, instructor_client: object) -> None:
        self._client = instructor_client

    def complete_applicability(self, block_text: str) -> str:
        client = self._client
        refresh = getattr(client, "refresh_config", None)
        if callable(refresh):
            refresh()
        raw_client = getattr(client, "_raw_client", None)
        model = getattr(client, "model", "local-model")
        if raw_client is None:
            msg = "InstructorApplicabilityLLM requires _raw_client"
            raise TypeError(msg)
        prompt = build_applicability_prompt(block_text)
        max_tokens = min(256, resolve_llm_max_compression_tokens())
        response = call_openai_with_transport_retries(
            lambda: raw_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": _APPLICABILITY_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=max_tokens,
            ),
        )
        choice = response.choices[0].message.content if response.choices else ""
        return sanitize_prose_llm_completion(choice or "")


__all__ = [
    "ApplicabilityLLM",
    "InstructorApplicabilityLLM",
    "build_applicability_prompt",
    "synthesize_applicability",
]
