"""Embedding clients for dual-vector block indexing."""

from __future__ import annotations

import threading
from typing import Protocol, runtime_checkable

from openai import OpenAI

from .config import EmbeddingSettings, embedding_settings


@runtime_checkable
class EmbeddingClient(Protocol):
    """Embed a single text string to a dense vector."""

    def embed_text(self, text: str) -> list[float]: ...


class OpenAICompatibleEmbeddingClient:
    """OpenAI-compatible ``/v1/embeddings`` client."""

    def __init__(self, settings: EmbeddingSettings | None = None) -> None:
        resolved = settings or embedding_settings()
        self._model = resolved.model
        self._client = OpenAI(
            base_url=resolved.base_url,
            api_key=resolved.api_key,
        )

    def embed_text(self, text: str) -> list[float]:
        cleaned = text.strip()
        if not cleaned:
            msg = "embed_text requires non-empty text"
            raise ValueError(msg)
        response = self._client.embeddings.create(
            model=self._model,
            input=cleaned,
        )
        data = response.data
        if not data:
            msg = "embedding API returned no vectors"
            raise RuntimeError(msg)
        vector = data[0].embedding
        return [float(x) for x in vector]


_client_lock = threading.Lock()
_cached_openai_embedding_client: OpenAICompatibleEmbeddingClient | None = None


def get_openai_embedding_client() -> OpenAICompatibleEmbeddingClient:
    """Reuse one OpenAI-compatible embeddings client per process."""
    global _cached_openai_embedding_client
    with _client_lock:
        if _cached_openai_embedding_client is None:
            _cached_openai_embedding_client = OpenAICompatibleEmbeddingClient()
        return _cached_openai_embedding_client


__all__ = [
    "EmbeddingClient",
    "OpenAICompatibleEmbeddingClient",
    "get_openai_embedding_client",
]
