"""Hybrid intent-based block retrieval over dual embeddings."""

from __future__ import annotations

import heapq
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from .config import dual_embedding_enabled, hybrid_weights
from .embedding import EmbeddingClient
from .math_util import cosine_similarity
from .store import (
    BlockVectorRecord,
    BlockVectorStore,
    _semantic_search_max_candidates,
    iter_block_records_from_disk,
)


def _lexical_rank_key(
    item: tuple[str, BlockVectorRecord],
    query: str,
) -> tuple[int, str]:
    _uuid, record = item
    tokens = [part.casefold() for part in query.split() if len(part) >= 2]
    blob = f"{record.block_text} {record.applicability_text}".casefold()
    lexical_hits = sum(1 for token in tokens if token in blob)
    return (lexical_hits, record.updated_at or "")


def _cap_records_for_scoring(
    records: Iterator[tuple[str, BlockVectorRecord]],
    query: str,
    cap: int,
) -> tuple[list[tuple[str, BlockVectorRecord]], int]:
    """Keep top ``cap`` records by lexical overlap without materializing the full index."""
    if cap <= 0:
        return [], 0

    heap: list[tuple[tuple[int, str], tuple[str, BlockVectorRecord]]] = []
    total = 0
    for item in records:
        total += 1
        key = _lexical_rank_key(item, query)
        if len(heap) < cap:
            heapq.heappush(heap, (key, item))
        elif key > heap[0][0]:
            heapq.heapreplace(heap, (key, item))

    if total <= cap:
        return [item for _key, item in heap], total

    ranked = sorted(heap, key=lambda entry: entry[0], reverse=True)
    return [item for _key, item in ranked], total


@dataclass(frozen=True, slots=True)
class BlockSearchHit:
    """One ranked block from hybrid search."""

    block_uuid: str
    page_title: str
    final_score: float
    score_content: float
    score_applicability: float
    applicability_text: str


def hybrid_block_search(
    graph_root: str | Path,
    query: str,
    *,
    embedding_client: EmbeddingClient,
    limit: int = 15,
) -> list[BlockSearchHit]:
    """Rank indexed blocks by weighted cosine similarity to ``query``."""
    if not dual_embedding_enabled():
        return []

    cleaned = query.strip()
    if not cleaned:
        return []

    root = Path(graph_root).expanduser().resolve(strict=False)
    cap = _semantic_search_max_candidates()
    records, total = _cap_records_for_scoring(
        iter_block_records_from_disk(root),
        cleaned,
        cap,
    )
    if not records:
        return []

    if total > cap:
        logger.warning(
            "Semantic index has {} blocks; scoring first {} "
            "(MATRYCA_SEMANTIC_SEARCH_MAX_CANDIDATES)",
            total,
            cap,
        )

    query_vec = embedding_client.embed_text(cleaned)
    weights = hybrid_weights()
    hits: list[BlockSearchHit] = []

    for block_uuid, record in records:
        score_content = cosine_similarity(query_vec, record.vec_content)
        score_app = cosine_similarity(query_vec, record.vec_applicability)
        final = (weights.content * score_content) + (weights.applicability * score_app)
        hits.append(
            BlockSearchHit(
                block_uuid=block_uuid,
                page_title=record.page_title,
                final_score=final,
                score_content=score_content,
                score_applicability=score_app,
                applicability_text=record.applicability_text,
            ),
        )

    hits.sort(key=lambda item: (-item.final_score, item.block_uuid))
    cap = max(1, min(limit, 100))
    return hits[:cap]


def format_semantic_search_markdown(
    graph_root: str | Path,
    query: str,
    *,
    embedding_client: EmbeddingClient,
    limit: int = 15,
) -> str:
    """Markdown report for MCP ``search_graph`` / ``method=semantic``."""
    root = Path(graph_root).expanduser().resolve(strict=False)
    weights = hybrid_weights()
    lines = [
        "# Semantic block search (dual embedding)",
        "",
        f"- **Graph:** `{root}`",
        f"- **Query:** `{query.strip()}`",
        f"- **Weights:** content={weights.content}, applicability={weights.applicability}",
        "",
    ]

    if not dual_embedding_enabled():
        lines.append(
            "_Dual embedding is disabled. Set `MATRYCA_DUAL_EMBEDDING_ENABLED=true` "
            "and let the daemon index pages after semantic writes._",
        )
        return "\n".join(lines) + "\n"

    hits = hybrid_block_search(
        root,
        query,
        embedding_client=embedding_client,
        limit=limit,
    )
    lines.append(f"- **Hits:** {len(hits)}")
    lines.append("")
    if not hits:
        store_path = BlockVectorStore.store_path(root)
        lines.append(
            f"_No indexed blocks in `{store_path.relative_to(root)}`. "
            "Wait for daemon semantic indexing with dual embedding enabled._",
        )
        return "\n".join(lines) + "\n"

    lines.append("## Ranked blocks")
    lines.append("")
    for hit in hits:
        lines.append(
            f"- `{hit.block_uuid}` on **{hit.page_title}** — "
            f"**{hit.final_score:.4f}** "
            f"(content={hit.score_content:.4f}, applicability={hit.score_applicability:.4f})",
        )
        if hit.applicability_text:
            lines.append(f"  - Applicability: {hit.applicability_text}")
    lines.append("")
    return "\n".join(lines) + "\n"


__all__ = [
    "BlockSearchHit",
    "format_semantic_search_markdown",
    "hybrid_block_search",
]
