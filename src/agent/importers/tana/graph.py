"""Tana flat ``docs[]`` graph indexes and entity placement heuristics."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from .load import iter_tana_nodes
from .schema import NodeDump

_STASH_SUFFIX = "_STASH"
_SCHEMA_SUFFIX = "_SCHEMA"
_TRASH_MARKER = "TRASH"
_SYS_PREFIX = "SYS_"

# Supertag definition names treated as standalone Logseq pages when applied.
_DEFAULT_PAGE_LIKE_SUPERTAGS = frozenset(
    {
        "page",
        "entity",
        "project",
        "person",
        "meeting",
        "company",
        "book",
        "article",
        "day",
    }
)


class EntityReason(StrEnum):
    """Why a Tana node maps to a Logseq page instead of an inline block."""

    FLAGS_LSB = "flags_lsb"
    LIBRARY = "library"
    PAGE_LIKE_SUPERTAG = "page_like_supertag"
    NOT_ENTITY = "not_entity"


@dataclass(frozen=True, slots=True)
class EntityDecision:
    """Outcome of entity-vs-block classification for one node."""

    is_entity: bool
    reason: EntityReason


@dataclass
class TanaWorkspaceGraph:
    """In-memory indexes over a streamed Tana workspace export."""

    nodes: dict[str, NodeDump]
    children_by_parent: dict[str, list[str]]
    parent_by_child: dict[str, str]
    schema_root_id: str | None
    stash_root_id: str | None
    tag_def_names: dict[str, str]
    page_like_supertags: frozenset[str]

    @classmethod
    def from_nodes(
        cls,
        nodes: Mapping[str, NodeDump],
        *,
        page_like_supertags: frozenset[str] | None = None,
    ) -> TanaWorkspaceGraph:
        builder = StreamingGraphBuilder(page_like_supertags=page_like_supertags)
        for node in nodes.values():
            builder.ingest_node(node)
        return builder.build()

    @classmethod
    def from_export(
        cls,
        export_path: Path,
        *,
        page_like_supertags: frozenset[str] | None = None,
        on_progress: Callable[[int], None] | None = None,
        progress_every: int = 1000,
    ) -> TanaWorkspaceGraph:
        builder = StreamingGraphBuilder(
            page_like_supertags=page_like_supertags,
            on_progress=on_progress,
            progress_every=progress_every,
        )
        for node in iter_tana_nodes(export_path):
            builder.ingest_node(node)
        return builder.build()

    @classmethod
    def from_iterable(
        cls,
        nodes: Iterable[NodeDump],
        *,
        page_like_supertags: frozenset[str] | None = None,
    ) -> TanaWorkspaceGraph:
        builder = StreamingGraphBuilder(page_like_supertags=page_like_supertags)
        for node in nodes:
            builder.ingest_node(node)
        return builder.build()

    def iter_children(self, parent_id: str) -> Iterator[NodeDump]:
        for child_id in self.children_by_parent.get(parent_id, ()):
            node = self.nodes.get(child_id)
            if node is not None:
                yield node

    def parent_id(self, node_id: str) -> str | None:
        return self.parent_by_child.get(node_id)

    def root_ids(self) -> list[str]:
        return [node_id for node_id in self.nodes if node_id not in self.parent_by_child]

    def is_system_node(self, node_id: str) -> bool:
        if node_id.startswith(_SYS_PREFIX):
            return True
        if _TRASH_MARKER in node_id:
            return True
        return node_id.endswith(_SCHEMA_SUFFIX)

    def is_in_library(self, node_id: str) -> bool:
        if self.stash_root_id is None:
            return False
        if node_id == self.stash_root_id:
            return True
        owner = self.nodes[node_id].props.get("_ownerId") if node_id in self.nodes else None
        if isinstance(owner, str) and owner == self.stash_root_id:
            return True
        parent = self.parent_by_child.get(node_id)
        while parent is not None:
            if parent == self.stash_root_id:
                return True
            parent = self.parent_by_child.get(parent)
        return False

    def classify_entity(self, node_id: str) -> EntityDecision:
        node = self.nodes.get(node_id)
        if node is None:
            return EntityDecision(is_entity=False, reason=EntityReason.NOT_ENTITY)
        if self.is_system_node(node_id):
            return EntityDecision(is_entity=False, reason=EntityReason.NOT_ENTITY)

        flags = node.props.get("_flags")
        if isinstance(flags, int) and flags % 2 == 1:
            return EntityDecision(is_entity=True, reason=EntityReason.FLAGS_LSB)

        if self.is_in_library(node_id):
            return EntityDecision(is_entity=True, reason=EntityReason.LIBRARY)

        if self._has_page_like_supertag(node):
            return EntityDecision(is_entity=True, reason=EntityReason.PAGE_LIKE_SUPERTAG)

        return EntityDecision(is_entity=False, reason=EntityReason.NOT_ENTITY)

    def _has_page_like_supertag(self, node: NodeDump) -> bool:
        meta_id = node.props.get("_metaNodeId")
        if not isinstance(meta_id, str):
            return False
        meta = self.nodes.get(meta_id)
        if meta is None:
            return False
        for child_id in meta.children:
            child = self.nodes.get(child_id)
            if child is None:
                continue
            for tag_id in child.children:
                tag_name = self.tag_def_names.get(tag_id, "").casefold()
                if tag_name in self.page_like_supertags:
                    return True
        return False


@dataclass
class StreamingGraphBuilder:
    """Incremental single-pass builder for :class:`TanaWorkspaceGraph`."""

    page_like_supertags: frozenset[str] | None = None
    on_progress: Callable[[int], None] | None = None
    progress_every: int = 1000

    def __post_init__(self) -> None:
        if self.page_like_supertags is None:
            self.page_like_supertags = _DEFAULT_PAGE_LIKE_SUPERTAGS
        self._nodes: dict[str, NodeDump] = {}
        self._children_by_parent: dict[str, list[str]] = {}
        self._parent_by_child: dict[str, str] = {}
        self._schema_root_id: str | None = None
        self._stash_root_id: str | None = None
        self._tag_def_names: dict[str, str] = {}

    def ingest_node(self, node: NodeDump) -> None:
        node_id = node.id
        self._nodes[node_id] = node
        if node_id.endswith(_SCHEMA_SUFFIX):
            self._schema_root_id = node_id
        elif node_id.endswith(_STASH_SUFFIX):
            self._stash_root_id = node_id

        doc_type = node.props.get("_docType")
        if doc_type == "tagDef":
            name = _node_display_name(node)
            if name:
                self._tag_def_names[node_id] = name

        for child_id in node.children:
            self._children_by_parent.setdefault(node_id, []).append(child_id)
            self._parent_by_child.setdefault(child_id, node_id)

        if self.on_progress is not None and self.progress_every > 0:
            count = len(self._nodes)
            if count % self.progress_every == 0:
                self.on_progress(count)

    def build(self) -> TanaWorkspaceGraph:
        for node_id, node in self._nodes.items():
            owner_id = node.props.get("_ownerId")
            if isinstance(owner_id, str) and owner_id in self._nodes:
                self._parent_by_child[node_id] = owner_id
        return TanaWorkspaceGraph(
            nodes=self._nodes,
            children_by_parent=self._children_by_parent,
            parent_by_child=self._parent_by_child,
            schema_root_id=self._schema_root_id,
            stash_root_id=self._stash_root_id,
            tag_def_names=self._tag_def_names,
            page_like_supertags=self.page_like_supertags,
        )


def build_graph_from_export(
    export_path: Path,
    *,
    on_progress: Callable[[int], None] | None = None,
    progress_every: int = 1000,
) -> TanaWorkspaceGraph:
    """Stream ``docs[]`` and build workspace indexes in one pass."""
    return TanaWorkspaceGraph.from_export(
        export_path,
        on_progress=on_progress,
        progress_every=progress_every,
    )


def _node_display_name(node: NodeDump) -> str:
    raw = node.props.get("name")
    if isinstance(raw, str):
        stripped = raw.strip()
        if stripped:
            return stripped
    return ""


__all__ = [
    "EntityDecision",
    "EntityReason",
    "StreamingGraphBuilder",
    "TanaWorkspaceGraph",
    "build_graph_from_export",
]
