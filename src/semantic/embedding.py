"""Embedding clients for dual-vector block indexing."""

from __future__ import annotations

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


__all__ = [
    "EmbeddingClient",
    "OpenAICompatibleEmbeddingClient",
]
