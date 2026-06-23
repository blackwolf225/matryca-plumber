"""Tests for Tana workspace graph indexes and entity heuristics."""

from __future__ import annotations

from pathlib import Path

import pytest
from src.agent.importers.tana.graph import (
    EntityReason,
    StreamingGraphBuilder,
    TanaWorkspaceGraph,
    build_graph_from_export,
)
from src.agent.importers.tana.schema import NodeDump

_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "tana"


def test_children_by_parent_and_parent_map() -> None:
    graph = build_graph_from_export(_FIXTURES / "minimal_direct.json")
    assert graph.children_by_parent["ROOT_A"] == ["CHILD_B"]
    assert graph.parent_by_child["CHILD_B"] == "ROOT_A"
    # REF_C is only linked via outbound_refs — not a structural child.
    assert "REF_C" not in graph.parent_by_child


def test_root_ids_exclude_children() -> None:
    graph = build_graph_from_export(_FIXTURES / "minimal_direct.json")
    roots = set(graph.root_ids())
    assert "ROOT_A" in roots
    assert "CHILD_B" not in roots
    assert "REF_C" in roots


def test_entity_flags_lsb() -> None:
    graph = build_graph_from_export(_FIXTURES / "entity_graph.json")
    decision = graph.classify_entity("FLAG_ENTITY")
    assert decision.is_entity is True
    assert decision.reason is EntityReason.FLAGS_LSB


def test_entity_library_owner_and_descendant() -> None:
    graph = build_graph_from_export(_FIXTURES / "entity_graph.json")
    assert graph.classify_entity("LIB_ITEM").reason is EntityReason.LIBRARY
    assert graph.classify_entity("DEEP_BLOCK").reason is EntityReason.LIBRARY


def test_plain_block_not_entity() -> None:
    graph = build_graph_from_export(_FIXTURES / "entity_graph.json")
    decision = graph.classify_entity("PLAIN")
    assert decision.is_entity is False
    assert decision.reason is EntityReason.NOT_ENTITY


def test_page_like_supertag_entity() -> None:
    graph = build_graph_from_export(_FIXTURES / "entity_graph.json")
    decision = graph.classify_entity("TAGGED")
    assert decision.is_entity is True
    assert decision.reason is EntityReason.PAGE_LIKE_SUPERTAG


def test_schema_and_stash_roots_detected() -> None:
    graph = build_graph_from_export(_FIXTURES / "entity_graph.json")
    assert graph.stash_root_id == "WS_STASH"
    assert graph.schema_root_id == "WS_SCHEMA"
    assert graph.tag_def_names["TAG_PROJECT"] == "project"


def test_from_iterable_builds_same_parent_map() -> None:
    nodes = [
        NodeDump(id="P", props={}, children=["C"]),
        NodeDump(id="C", props={}, children=[]),
    ]
    graph = TanaWorkspaceGraph.from_iterable(nodes)
    assert graph.parent_by_child["C"] == "P"
    assert list(graph.iter_children("P"))[0].id == "C"


def test_streaming_builder_matches_from_export() -> None:
    export = _FIXTURES / "entity_graph.json"
    direct = build_graph_from_export(export)
    builder = StreamingGraphBuilder()
    for node in direct.nodes.values():
        builder.ingest_node(node)
    built = builder.build()
    assert built.schema_root_id == direct.schema_root_id
    assert built.stash_root_id == direct.stash_root_id
    assert built.tag_def_names == direct.tag_def_names
    assert built.parent_by_child == direct.parent_by_child
    assert set(built.nodes) == set(direct.nodes)


def test_from_export_single_pass_no_load_tana_nodes_by_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.agent.importers.tana.load as load_mod

    def _forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("load_tana_nodes_by_id must not run during from_export")

    monkeypatch.setattr(load_mod, "load_tana_nodes_by_id", _forbidden)
    graph = TanaWorkspaceGraph.from_export(_FIXTURES / "minimal_direct.json")
    assert len(graph.nodes) == 3
