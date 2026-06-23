"""Tests for Tana supertag and field tuple decoding."""

from __future__ import annotations

from datetime import UTC, datetime

from src.agent.importers.tana.graph import TanaWorkspaceGraph
from src.agent.importers.tana.html import plain_text_from_tana_html
from src.agent.importers.tana.schema import NodeDump
from src.agent.importers.tana.tags import (
    TanaTagsExtractor,
    format_property_line,
    normalize_logseq_property_key,
)


def _build_field_graph() -> TanaWorkspaceGraph:
    nodes = {
        "DATA": NodeDump(
            id="DATA",
            props={"name": "Task item", "_metaNodeId": "META_FIELDS"},
            children=[],
        ),
        "META_FIELDS": NodeDump(
            id="META_FIELDS",
            props={},
            children=["T_TAG", "T_TEXT", "T_DATE", "T_CB", "T_URL", "T_REF"],
        ),
        "T_TAG": NodeDump(id="T_TAG", props={"_docType": "tuple"}, children=["TAG_DEF"]),
        "TAG_DEF": NodeDump(
            id="TAG_DEF",
            props={"name": "project", "_docType": "tagDef"},
            children=[],
        ),
        "T_TEXT": NodeDump(
            id="T_TEXT",
            props={"_docType": "tuple"},
            children=["LBL_STATUS", "VAL_STATUS"],
        ),
        "LBL_STATUS": NodeDump(
            id="LBL_STATUS",
            props={"name": "<span>Target Date</span>"},
            children=[],
        ),
        "VAL_STATUS": NodeDump(id="VAL_STATUS", props={"name": "In progress"}, children=[]),
        "T_DATE": NodeDump(
            id="T_DATE",
            props={"_docType": "tuple", "_sourceId": "ATTR_DUE"},
            children=["LBL_DUE", "VAL_DUE"],
        ),
        "LBL_DUE": NodeDump(id="LBL_DUE", props={"name": "Due date"}, children=[]),
        "VAL_DUE": NodeDump(
            id="VAL_DUE",
            props={"created": int(datetime(2026, 3, 15, tzinfo=UTC).timestamp() * 1000)},
            children=[],
        ),
        "ATTR_DUE": NodeDump(
            id="ATTR_DUE",
            props={"name": "Due date", "_docType": "attrDef"},
            children=["TYPE_DUE"],
        ),
        "TYPE_DUE": NodeDump(
            id="TYPE_DUE",
            props={"_docType": "tuple", "_sourceId": "SYS_A02"},
            children=["SYS_T06", "SYS_D03"],
        ),
        "T_CB": NodeDump(
            id="T_CB",
            props={"_docType": "tuple", "_sourceId": "ATTR_ACTIVE"},
            children=["LBL_ACTIVE", "VAL_ACTIVE"],
        ),
        "LBL_ACTIVE": NodeDump(id="LBL_ACTIVE", props={"name": "Is Active"}, children=[]),
        "VAL_ACTIVE": NodeDump(id="VAL_ACTIVE", props={"done": True}, children=[]),
        "ATTR_ACTIVE": NodeDump(
            id="ATTR_ACTIVE",
            props={"name": "Is Active", "_docType": "attrDef"},
            children=["TYPE_ACTIVE"],
        ),
        "TYPE_ACTIVE": NodeDump(
            id="TYPE_ACTIVE",
            props={"_docType": "tuple", "_sourceId": "SYS_A02"},
            children=["SYS_T06", "SYS_D01"],
        ),
        "T_URL": NodeDump(
            id="T_URL",
            props={"_docType": "tuple", "_sourceId": "ATTR_URL"},
            children=["LBL_SOURCE", "VAL_SOURCE"],
        ),
        "LBL_SOURCE": NodeDump(id="LBL_SOURCE", props={"name": "Source URL"}, children=[]),
        "VAL_SOURCE": NodeDump(
            id="VAL_SOURCE",
            props={"name": "https://example.com/doc"},
            children=[],
        ),
        "ATTR_URL": NodeDump(
            id="ATTR_URL",
            props={"name": "Source URL", "_docType": "attrDef"},
            children=["TYPE_URL"],
        ),
        "TYPE_URL": NodeDump(
            id="TYPE_URL",
            props={"_docType": "tuple", "_sourceId": "SYS_A02"},
            children=["SYS_T06", "SYS_D10"],
        ),
        "T_REF": NodeDump(
            id="T_REF",
            props={"_docType": "tuple", "_sourceId": "ATTR_REF"},
            children=["LBL_OWNER", "VAL_OWNER"],
        ),
        "LBL_OWNER": NodeDump(id="LBL_OWNER", props={"name": "Owner"}, children=[]),
        "VAL_OWNER": NodeDump(
            id="VAL_OWNER",
            props={},
            children=["PERSON"],
            outbound_refs=["PERSON"],
        ),
        "PERSON": NodeDump(id="PERSON", props={"name": "Marco Porcellato"}, children=[]),
        "ATTR_REF": NodeDump(
            id="ATTR_REF",
            props={"name": "Owner", "_docType": "attrDef"},
            children=["TYPE_REF"],
        ),
        "TYPE_REF": NodeDump(
            id="TYPE_REF",
            props={"_docType": "tuple", "_sourceId": "SYS_A02"},
            children=["SYS_T06", "SYS_D05"],
        ),
    }
    return TanaWorkspaceGraph.from_nodes(nodes)


def test_plain_text_from_tana_html_strips_tags() -> None:
    assert plain_text_from_tana_html('<span class="ref">Target Date</span>') == "Target Date"


def test_normalize_logseq_property_key() -> None:
    assert normalize_logseq_property_key("Target Date") == "target-date"
    assert normalize_logseq_property_key("Is_Active") == "is-active"
    assert normalize_logseq_property_key('<a href="#">Due #1</a>') == "due-1"


def test_extract_supertag_from_meta_node() -> None:
    graph = _build_field_graph()
    result = TanaTagsExtractor(graph).extract_for_node("DATA")
    assert result.supertag_names == ["project"]


def test_text_field_without_source_id_uses_label_inference() -> None:
    graph = _build_field_graph()
    result = TanaTagsExtractor(graph).extract_for_node("DATA")
    by_key = {line.key: line for line in result.properties}
    assert "target-date" in by_key
    assert by_key["target-date"].value == "In progress"
    assert by_key["target-date"].tana_field_def_id is None


def test_date_field_emits_journal_link_for_day_key() -> None:
    graph = _build_field_graph()
    extractor = TanaTagsExtractor(graph, journal_page_title_format="yyyy-MM-dd")
    result = extractor.extract_for_node("DATA")
    by_key = {line.key: line for line in result.properties}
    assert by_key["due-date"].value == "[[2026-03-15]]"
    assert by_key["due-date"].data_type == "SYS_D03"


def test_checkbox_field_emits_boolean_not_todo_marker() -> None:
    graph = _build_field_graph()
    result = TanaTagsExtractor(graph).extract_for_node("DATA")
    by_key = {line.key: line for line in result.properties}
    assert by_key["is-active"].value == "true"
    assert "TODO" not in format_property_line(by_key["is-active"])
    assert "DONE" not in format_property_line(by_key["is-active"])


def test_url_field_maps_source_key() -> None:
    graph = _build_field_graph()
    result = TanaTagsExtractor(graph).extract_for_node("DATA")
    by_key = {line.key: line for line in result.properties}
    assert "source" in by_key
    assert by_key["source"].value == "https://example.com/doc"


def test_reference_field_emits_wikilink() -> None:
    graph = _build_field_graph()
    result = TanaTagsExtractor(graph).extract_for_node("DATA")
    by_key = {line.key: line for line in result.properties}
    assert by_key["owner"].value == "[[Marco Porcellato]]"


def test_mega_tuple_skipped_with_warning() -> None:
    child_ids = [f"C{i}" for i in range(51)]
    nodes = {
        "N": NodeDump(id="N", props={"_metaNodeId": "META"}, children=[]),
        "META": NodeDump(id="META", props={}, children=["MEGA"]),
        "MEGA": NodeDump(id="MEGA", props={"_docType": "tuple"}, children=child_ids),
    }
    for cid in child_ids:
        nodes[cid] = NodeDump(id=cid, props={"name": "x"}, children=[])
    graph = TanaWorkspaceGraph.from_nodes(nodes)
    result = TanaTagsExtractor(graph).extract_for_node("N")
    assert result.properties == []
    assert any("mega-tuple" in warning for warning in result.warnings)


def test_non_day_date_field_emits_iso() -> None:
    nodes = {
        "N": NodeDump(id="N", props={"_metaNodeId": "META"}, children=[]),
        "META": NodeDump(id="META", props={}, children=["TUPLE"]),
        "TUPLE": NodeDump(id="TUPLE", props={"_docType": "tuple"}, children=["LBL", "VAL"]),
        "LBL": NodeDump(id="LBL", props={"name": "Updated at"}, children=[]),
        "VAL": NodeDump(
            id="VAL",
            props={"created": int(datetime(2026, 1, 5, tzinfo=UTC).timestamp() * 1000)},
            children=[],
        ),
        "ATTR": NodeDump(
            id="ATTR",
            props={"name": "Updated at", "_docType": "attrDef"},
            children=["TYPE"],
        ),
        "TYPE": NodeDump(
            id="TYPE",
            props={"_docType": "tuple", "_sourceId": "SYS_A02"},
            children=["SYS_T06", "SYS_D03"],
        ),
    }
    graph = TanaWorkspaceGraph.from_nodes(nodes)
    result = TanaTagsExtractor(graph).extract_for_node("N")
    assert result.properties[0].key == "updated-at"
    assert result.properties[0].value == "2026-01-05"
