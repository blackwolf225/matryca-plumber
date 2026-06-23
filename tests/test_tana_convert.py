"""Tests for Tana → Logseq hybrid placement conversion."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from src.agent.importers.tana.convert import TanaConverter, convert_tana_graph
from src.agent.importers.tana.graph import TanaWorkspaceGraph
from src.agent.importers.tana.provenance import PROP_TANA_DEPTH_SPLIT, PROP_TANA_ID
from src.agent.importers.tana.schema import NodeDump
from src.agent.outline_models import OutlineNode

_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "tana"


def _outline_depth(node: OutlineNode, current: int = 0) -> int:
    if not node.children:
        return current
    return max(_outline_depth(child, current + 1) for child in node.children)


def _find_nodes_matching(
    node: OutlineNode,
    predicate: Callable[[OutlineNode], bool],
) -> list[OutlineNode]:
    found: list[OutlineNode] = []
    if predicate(node):
        found.append(node)
    for child in node.children:
        found.extend(_find_nodes_matching(child, predicate))
    return found


def _build_convert_graph() -> TanaWorkspaceGraph:
    """Entity with fields, nested children, and a deep chain for split testing."""
    nodes = {
        "ENT": NodeDump(
            id="ENT",
            props={"name": "My Project", "_flags": 1, "_metaNodeId": "META_ENT"},
            children=["CHILD_A"],
        ),
        "META_ENT": NodeDump(
            id="META_ENT",
            props={},
            children=["T_TAG", "T_STATUS"],
        ),
        "T_TAG": NodeDump(id="T_TAG", props={"_docType": "tuple"}, children=["TAG_PROJECT"]),
        "TAG_PROJECT": NodeDump(
            id="TAG_PROJECT",
            props={"name": "project", "_docType": "tagDef"},
            children=[],
        ),
        "T_STATUS": NodeDump(
            id="T_STATUS",
            props={"_docType": "tuple"},
            children=["LBL_STATUS", "VAL_STATUS"],
        ),
        "LBL_STATUS": NodeDump(id="LBL_STATUS", props={"name": "Status"}, children=[]),
        "VAL_STATUS": NodeDump(id="VAL_STATUS", props={"name": "Active"}, children=[]),
        "CHILD_A": NodeDump(
            id="CHILD_A",
            props={"name": "First task", "_done": True},
            children=["DEEP_1"],
        ),
        "DEEP_1": NodeDump(id="DEEP_1", props={"name": "Level 1"}, children=["DEEP_2"]),
        "DEEP_2": NodeDump(id="DEEP_2", props={"name": "Level 2"}, children=["DEEP_3"]),
        "DEEP_3": NodeDump(id="DEEP_3", props={"name": "Level 3"}, children=["DEEP_4"]),
        "DEEP_4": NodeDump(id="DEEP_4", props={"name": "Level 4"}, children=[]),
        "DAY": NodeDump(
            id="DAY",
            props={
                "name": "2026-03-20",
                "_metaNodeId": "META_DAY",
                "created": int(datetime(2026, 3, 20, tzinfo=UTC).timestamp() * 1000),
            },
            children=["DAY_CHILD"],
        ),
        "META_DAY": NodeDump(id="META_DAY", props={}, children=["T_DAY"]),
        "T_DAY": NodeDump(id="T_DAY", props={"_docType": "tuple"}, children=["TAG_DAY"]),
        "TAG_DAY": NodeDump(
            id="TAG_DAY",
            props={"name": "day", "_docType": "tagDef"},
            children=[],
        ),
        "DAY_CHILD": NodeDump(id="DAY_CHILD", props={"name": "Journal note"}, children=[]),
    }
    return TanaWorkspaceGraph.from_nodes(nodes)


def test_entity_page_title_and_properties() -> None:
    graph = _build_convert_graph()
    result = convert_tana_graph(graph, max_depth=8, export_file="mini.json")

    project_pages = [p for p in result.pages if p.page_title == "Tana/project/My Project"]
    assert len(project_pages) == 1
    page = project_pages[0]
    assert page.page_properties[PROP_TANA_ID] == "ENT"
    assert "tana-import" in page.page_properties["tags"]
    assert page.page_properties["type"] == "project"

    root = page.outline_roots[0]
    assert root.text == "My Project"
    assert root.properties[PROP_TANA_ID] == "ENT"
    assert "id" not in root.properties
    assert "id::" not in root.properties


def test_field_properties_and_done_prefix() -> None:
    graph = _build_convert_graph()
    result = convert_tana_graph(graph, max_depth=8)
    page = next(p for p in result.pages if p.page_title == "Tana/project/My Project")
    root = page.outline_roots[0]
    assert root.properties["status"] == "Active"
    child = root.children[0]
    assert child.text.startswith("DONE ")
    assert "TODO" not in child.properties.values()
    assert child.properties[PROP_TANA_ID] == "CHILD_A"


def test_depth_split_creates_split_page_and_link() -> None:
    graph = _build_convert_graph()
    result = convert_tana_graph(graph, max_depth=4)

    split_pages = [
        page
        for page in result.pages
        if page.page_properties.get(PROP_TANA_DEPTH_SPLIT) == "true"
    ]
    assert len(split_pages) == 1
    assert split_pages[0].page_title == "Tana/Split/Level 3"
    assert result.depth_splits == 1

    project_page = next(p for p in result.pages if p.page_title == "Tana/project/My Project")
    link_nodes = _find_nodes_matching(
        project_page.outline_roots[0],
        lambda node: node.text.startswith("[[Tana/Split/"),
    )
    assert link_nodes
    assert link_nodes[0].properties[PROP_TANA_DEPTH_SPLIT] == "true"

    assert _outline_depth(project_page.outline_roots[0]) <= 4


def test_journal_routing_for_day_node() -> None:
    graph = _build_convert_graph()
    result = convert_tana_graph(
        graph,
        max_depth=8,
        journal_page_title_format="yyyy-MM-dd",
    )
    assert len(result.journals) == 1
    journal = result.journals[0]
    assert journal.page_title == "2026-03-20"
    assert journal.relative_path == "journals/2026-03-20.md"
    assert journal.outline_roots[0].text.endswith("#day")
    assert journal.outline_roots[0].children[0].text == "Journal note"


def test_convert_from_fixture_export() -> None:
    graph = TanaWorkspaceGraph.from_export(_FIXTURES / "entity_graph.json")
    result = TanaConverter(graph, max_depth=8).convert()
    titles = {page.page_title for page in result.pages}
    assert "Tana/project/My project" in titles
    assert "Tana/Library entity" in titles
