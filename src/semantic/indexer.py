"""Index Logseq blocks with dual content + applicability embeddings."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from logseq_matryca_parser.logos_core import LogseqNode
from loguru import logger

from ..daemon.ast_cache import get_graph_ast_cache
from .applicability import ApplicabilityLLM, synthesize_applicability
from .config import dual_embedding_enabled
from .embedding import EmbeddingClient
from .store import BlockVectorRecord, load_block_vector_store


def _block_uuid(node: LogseqNode) -> str | None:
    raw = node.properties.get("id") or node.uuid
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def _block_text(node: LogseqNode) -> str:
    parts = [node.content or "", node.clean_text or ""]
    return " ".join(part.strip() for part in parts if part.strip()).strip()


def _iter_indexable_nodes(roots: list[LogseqNode]) -> list[LogseqNode]:
    collected: list[LogseqNode] = []

    def walk(node: LogseqNode) -> None:
        if _block_uuid(node) and _block_text(node):
            collected.append(node)
        for child in node.children:
            walk(child)

    for root in roots:
        walk(root)
    return collected


def index_page_blocks(
    graph_root: Path,
    page_path: Path,
    page_title: str,
    *,
    llm_client: ApplicabilityLLM,
    embedding_client: EmbeddingClient,
) -> int:
    """Dual-embed all blocks with ``id::`` on ``page_title``. Returns blocks indexed."""
    if not dual_embedding_enabled():
        return 0

    root = graph_root.expanduser().resolve(strict=False)
    cache = get_graph_ast_cache(root)
    cache.apply_file_event(page_path, "modified")
    graph = cache.get_graph()
    page = graph.pages.get(page_title)
    if page is None:
        logger.bind(page=page_title).debug("Skipping dual embed: page not in AST cache")
        return 0

    nodes = _iter_indexable_nodes(list(page.root_nodes))
    if not nodes:
        return 0

    store = load_block_vector_store(root)
    indexed = 0
    now = datetime.now(tz=UTC).isoformat()

    for node in nodes:
        block_id = _block_uuid(node)
        if block_id is None:
            continue
        text = _block_text(node)
        if not text:
            continue
        try:
            applicability = synthesize_applicability(text, llm_client)
            vec_content = embedding_client.embed_text(text)
            vec_app = embedding_client.embed_text(applicability)
        except Exception as exc:  # noqa: BLE001 — best-effort per block
            logger.bind(uuid=block_id, page=page_title).warning(
                "Dual embedding failed for block: {}",
                exc,
            )
            continue

        store.upsert(
            block_id,
            BlockVectorRecord(
                page_title=page_title,
                block_text=text,
                applicability_text=applicability,
                vec_content=vec_content,
                vec_applicability=vec_app,
                updated_at=now,
            ),
        )
        indexed += 1

    if indexed > 0:
        store.save()
    logger.bind(page=page_title, blocks=indexed).info("Dual embedding indexed blocks")
    return indexed


__all__ = ["index_page_blocks"]
