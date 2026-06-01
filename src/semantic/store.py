"""Persistent dual-vector index per block UUID (JSON under semantic cache)."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from loguru import logger

BLOCK_VECTORS_FILENAME = "block_vectors.json"
BLOCK_VECTORS_VERSION = 1

_lock = threading.Lock()
_loaded: dict[str, BlockVectorStore] = {}


@dataclass(slots=True)
class BlockVectorRecord:
    """Dual embeddings for one Logseq block."""

    page_title: str
    block_text: str
    applicability_text: str
    vec_content: list[float]
    vec_applicability: list[float]
    updated_at: str = ""

    def to_json(self) -> dict[str, Any]:
        return {
            "page_title": self.page_title,
            "block_text": self.block_text,
            "applicability_text": self.applicability_text,
            "vec_content": self.vec_content,
            "vec_applicability": self.vec_applicability,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> BlockVectorRecord:
        return cls(
            page_title=str(payload.get("page_title", "")),
            block_text=str(payload.get("block_text", "")),
            applicability_text=str(payload.get("applicability_text", "")),
            vec_content=[float(x) for x in payload.get("vec_content", [])],
            vec_applicability=[float(x) for x in payload.get("vec_applicability", [])],
            updated_at=str(payload.get("updated_at", "")),
        )


@dataclass
class BlockVectorStore:
    """In-memory block vector catalog backed by ``.matryca_semantic_cache/block_vectors.json``."""

    graph_root: Path
    version: int = BLOCK_VECTORS_VERSION
    updated_at: str | None = None
    blocks: dict[str, BlockVectorRecord] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    @staticmethod
    def store_path(graph_root: Path) -> Path:
        return graph_root / ".matryca_semantic_cache" / BLOCK_VECTORS_FILENAME

    def to_json(self) -> dict[str, Any]:
        with self._lock:
            payload = {
                str(uuid): rec.to_json() for uuid, rec in sorted(self.blocks.items())
            }
        return {
            "version": self.version,
            "updated_at": self.updated_at,
            "blocks": payload,
        }

    @classmethod
    def from_json(cls, graph_root: Path, payload: dict[str, Any]) -> BlockVectorStore:
        blocks: dict[str, BlockVectorRecord] = {}
        raw = payload.get("blocks", {})
        if isinstance(raw, dict):
            for block_uuid, rec in raw.items():
                if isinstance(rec, dict):
                    blocks[str(block_uuid)] = BlockVectorRecord.from_json(rec)
        return cls(
            graph_root=graph_root,
            version=int(payload.get("version", BLOCK_VECTORS_VERSION)),
            updated_at=payload.get("updated_at"),
            blocks=blocks,
        )

    def upsert(self, block_uuid: str, record: BlockVectorRecord) -> None:
        with self._lock:
            self.blocks[block_uuid] = record

    def iter_records(self) -> list[tuple[str, BlockVectorRecord]]:
        with self._lock:
            return list(self.blocks.items())

    def save(self) -> None:
        path = self.store_path(self.graph_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            self.updated_at = datetime.now(tz=UTC).isoformat()
            payload = {
                "version": self.version,
                "updated_at": self.updated_at,
                "blocks": {
                    str(block_uuid): record.to_json()
                    for block_uuid, record in sorted(self.blocks.items())
                },
            }
            data = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        path.write_text(data, encoding="utf-8")


def load_block_vector_store(
    graph_root: Path,
    *,
    force_reload: bool = False,
) -> BlockVectorStore:
    """Load or create the block vector store for ``graph_root``."""
    key = str(graph_root.expanduser().resolve(strict=False))
    with _lock:
        if not force_reload and key in _loaded:
            return _loaded[key]

        path = BlockVectorStore.store_path(Path(key))
        store = BlockVectorStore(graph_root=Path(key))
        if path.is_file():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    store = BlockVectorStore.from_json(Path(key), payload)
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("Failed to load block_vectors.json: {}", exc)
        _loaded[key] = store
        return store


def clear_block_vector_store_cache() -> None:
    """Drop in-memory stores (tests)."""
    with _lock:
        _loaded.clear()


__all__ = [
    "BLOCK_VECTORS_FILENAME",
    "BLOCK_VECTORS_VERSION",
    "BlockVectorRecord",
    "BlockVectorStore",
    "clear_block_vector_store_cache",
    "load_block_vector_store",
]
