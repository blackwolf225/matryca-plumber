"""Pure-Python vector math for hybrid semantic search (no numpy)."""

from __future__ import annotations

import math


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity; returns ``0.0`` on empty or length mismatch."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for x, y in zip(a, b, strict=True):
        dot += x * y
        norm_a += x * x
        norm_b += y * y
    if norm_a <= 0.0 or norm_b <= 0.0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


def hybrid_score(
    query_vec: list[float],
    vec_content: list[float],
    vec_applicability: list[float],
    *,
    weight_content: float,
    weight_applicability: float,
) -> float:
    """Weighted sum of content and applicability cosine similarities."""
    score_content = cosine_similarity(query_vec, vec_content)
    score_app = cosine_similarity(query_vec, vec_applicability)
    return (weight_content * score_content) + (weight_applicability * score_app)


__all__ = ["cosine_similarity", "hybrid_score"]
