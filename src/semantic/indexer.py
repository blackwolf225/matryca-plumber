"""Index Logseq blocks with dual content + applicability embeddings."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage
from loguru import logger

from ..daemon.ast_cache import get_graph_ast_cache
from .applicability import ApplicabilityLLM, synthesize_applicability
from .config import SemanticRuntimeConfig
from .embedding import EmbeddingClient
from .store import (
    BlockVectorRecord,
    apply_page_block_vector_updates,
    release_block_vector_store,
)


def _block_uuid(node: LogseqNode) -> str | None:
    raw = node.properties.get("id") or node.uuid
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def _block_text(node: LogseqNode) -> str:
    parts: list[str] = []
    for raw in (node.content or "", node.clean_text or ""):
        text = raw.strip()
        if text and text not in parts:
            parts.append(text)
    return " ".join(parts).strip()


def _prune_page_vectors(graph_root: Path, page_title: str, keep_uuids: set[str]) -> int:
    _indexed, pruned = apply_page_block_vector_updates(
        graph_root,
        page_title,
        upserts={},
        keep_uuids=keep_uuids,
    )
    if pruned > 0:
        release_block_vector_store(graph_root)
    return pruned


def _resolve_page_in_graph(graph: object, page_title: str) -> tuple[LogseqPage | None, str]:
    """Return ``(page, canonical_title)`` using the graph's page map key when possible."""
    pages = getattr(graph, "pages", None)
    if not isinstance(pages, dict):
        return None, page_title
    direct = pages.get(page_title)
    if direct is not None:
        return direct, page_title
    fold = page_title.casefold()
    for key, candidate in pages.items():
        if isinstance(key, str) and key.casefold() == fold:
            return candidate, key
    return None, page_title


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


def _indexable_block_ids(nodes: list[LogseqNode]) -> set[str]:
    ids: set[str] = set()
    for node in nodes:
        block_id = _block_uuid(node)
        if block_id and _block_text(node):
            ids.add(block_id)
    return ids


def index_page_blocks(
    graph_root: Path,
    page_path: Path,
    page_title: str,
    *,
    llm_client: ApplicabilityLLM,
    embedding_client: EmbeddingClient,
    runtime_config: SemanticRuntimeConfig | None = None,
) -> int:
    """Dual-embed all blocks with ``id::`` on ``page_title``. Returns blocks indexed."""
    config = runtime_config or SemanticRuntimeConfig.from_env()
    if not config.dual_embedding_enabled:
        return 0

    root = graph_root.expanduser().resolve(strict=False)
    cache = get_graph_ast_cache(root)
    cache.apply_file_event(page_path, "modified")
    graph = cache.get_graph()
    page, canonical_title = _resolve_page_in_graph(graph, page_title)
    if page is None:
        logger.bind(page=page_title).debug(
            "Skipping dual embed: page not in AST cache (vectors left unchanged)",
        )
        return 0

    nodes = _iter_indexable_nodes(list(page.root_nodes))
    keep_uuids = _indexable_block_ids(nodes)
    if not nodes:
        _prune_page_vectors(root, canonical_title, keep_uuids)
        return 0

    upserts: dict[str, BlockVectorRecord] = {}
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
            logger.bind(uuid=block_id, page=canonical_title).warning(
                "Dual embedding failed for block: {}",
                exc,
            )
            continue

        upserts[block_id] = BlockVectorRecord(
            page_title=canonical_title,
            block_text=text,
            applicability_text=applicability,
            vec_content=vec_content,
            vec_applicability=vec_app,
            updated_at=now,
        )

    indexed, _pruned = apply_page_block_vector_updates(
        root,
        canonical_title,
        upserts=upserts,
        keep_uuids=keep_uuids,
    )
    release_block_vector_store(graph_root)
    logger.bind(page=canonical_title, blocks=indexed).info("Dual embedding indexed blocks")
    return indexed


__all__ = ["index_page_blocks"]
