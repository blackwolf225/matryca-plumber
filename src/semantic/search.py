"""Hybrid intent-based block retrieval over dual embeddings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import dual_embedding_enabled, hybrid_weights
from .embedding import EmbeddingClient
from .math_util import cosine_similarity, hybrid_score
from .store import BlockVectorStore, load_block_vector_store


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
    store = load_block_vector_store(root)
    records = store.iter_records()
    if not records:
        return []

    query_vec = embedding_client.embed_text(cleaned)
    weights = hybrid_weights()
    hits: list[BlockSearchHit] = []

    for block_uuid, record in records:
        score_content = cosine_similarity(query_vec, record.vec_content)
        score_app = cosine_similarity(query_vec, record.vec_applicability)
        final = hybrid_score(
            query_vec,
            record.vec_content,
            record.vec_applicability,
            weight_content=weights.content,
            weight_applicability=weights.applicability,
        )
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
