"""Streaming loader for Tana workspace JSON exports (``ijson`` — no ``json.load``)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import ijson
from loguru import logger
from pydantic import ValidationError

from .schema import NodeDump

_DOCS_PREFIX_DIRECT = "docs.item"
_DOCS_PREFIX_STORE = "storeData.docs.item"
_PEEK_BYTES = 8192


def detect_docs_ijson_prefix(export_path: Path) -> str:
    """Return the ``ijson`` prefix for ``docs[]`` (direct or ``storeData`` wrapper)."""
    with export_path.open("rb") as handle:
        head = handle.read(_PEEK_BYTES)
    if b'"storeData"' in head:
        return _DOCS_PREFIX_STORE
    return _DOCS_PREFIX_DIRECT


def _coerce_raw_node(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    node_id = raw.get("id")
    if not isinstance(node_id, str) or not node_id.strip():
        return None
    return raw


def iter_tana_nodes(export_path: Path) -> Iterator[NodeDump]:
    """Yield validated ``NodeDump`` nodes from a Tana export file via ``ijson`` streaming.

    Uses binary stream parsing — the full JSON DOM is never materialized.
    Malformed nodes are logged and skipped.
    """
    prefix = detect_docs_ijson_prefix(export_path)
    with export_path.open("rb") as handle:
        for raw in ijson.items(handle, prefix):
            payload = _coerce_raw_node(raw)
            if payload is None:
                logger.debug("Skipping non-object or id-less docs[] entry in {}", export_path)
                continue
            try:
                yield NodeDump.model_validate(payload)
            except ValidationError as exc:
                node_id = payload.get("id", "<unknown>")
                logger.warning("Invalid Tana node {} in {}: {}", node_id, export_path, exc)
                continue


def load_tana_nodes_by_id(export_path: Path) -> dict[str, NodeDump]:
    """Stream ``docs[]`` and build an ``id → NodeDump`` index (O(nodes) memory)."""
    return {node.id: node for node in iter_tana_nodes(export_path)}


__all__ = [
    "detect_docs_ijson_prefix",
    "iter_tana_nodes",
    "load_tana_nodes_by_id",
]
