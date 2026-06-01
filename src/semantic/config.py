"""Environment-driven configuration for dual block embeddings."""

from __future__ import annotations

import os
from dataclasses import dataclass

from ..agent.plumber_config import (
    _env_bool,
    _env_float,
    _env_str,
    resolve_llm_api_key,
    resolve_llm_base_url,
)

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_WEIGHT_CONTENT = 0.5
DEFAULT_WEIGHT_APPLICABILITY = 0.5


@dataclass(frozen=True, slots=True)
class HybridWeights:
    """Weights for hybrid cosine retrieval."""

    content: float
    applicability: float


@dataclass(frozen=True, slots=True)
class EmbeddingSettings:
    """Resolved embedding API settings."""

    base_url: str
    model: str
    api_key: str


def dual_embedding_enabled() -> bool:
    """Return whether daemon should dual-index blocks after semantic writes."""
    return _env_bool("MATRYCA_DUAL_EMBEDDING_ENABLED", default=False)


def resolve_embedding_base_url() -> str:
    """``MATRYCA_EMBEDDING_BASE_URL`` or fall back to chat LLM base URL."""
    override = os.environ.get("MATRYCA_EMBEDDING_BASE_URL", "").strip()
    if override:
        return resolve_llm_base_url(override=override)
    return resolve_llm_base_url()


def resolve_embedding_model() -> str:
    return _env_str("MATRYCA_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)


def embedding_settings() -> EmbeddingSettings:
    return EmbeddingSettings(
        base_url=resolve_embedding_base_url(),
        model=resolve_embedding_model(),
        api_key=resolve_llm_api_key(),
    )


def hybrid_weights() -> HybridWeights:
    content = _env_float("MATRYCA_WEIGHT_CONTENT", DEFAULT_WEIGHT_CONTENT)
    applicability = _env_float("MATRYCA_WEIGHT_APPLICABILITY", DEFAULT_WEIGHT_APPLICABILITY)
    return HybridWeights(content=content, applicability=applicability)


__all__ = [
    "DEFAULT_EMBEDDING_MODEL",
    "DEFAULT_WEIGHT_APPLICABILITY",
    "DEFAULT_WEIGHT_CONTENT",
    "EmbeddingSettings",
    "HybridWeights",
    "dual_embedding_enabled",
    "embedding_settings",
    "hybrid_weights",
    "resolve_embedding_base_url",
    "resolve_embedding_model",
]
