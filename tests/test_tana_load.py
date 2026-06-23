"""Tests for Tana JSON streaming loader and Logseq config.edn journal format."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from src.agent.importers.tana.load import (
    detect_docs_ijson_prefix,
    iter_tana_nodes,
    load_tana_nodes_by_id,
)
from src.agent.importers.tana.schema import NodeDump
from src.graph.logseq_config import (
    DEFAULT_JOURNAL_PAGE_TITLE_FORMAT,
    get_logseq_journal_format,
)

_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "tana"


def test_detect_docs_ijson_prefix_direct() -> None:
    path = _FIXTURES / "minimal_direct.json"
    assert detect_docs_ijson_prefix(path) == "docs.item"


def test_detect_docs_ijson_prefix_store_data_wrapper() -> None:
    path = _FIXTURES / "minimal_store_data.json"
    assert detect_docs_ijson_prefix(path) == "storeData.docs.item"


def test_iter_tana_nodes_direct_export() -> None:
    path = _FIXTURES / "minimal_direct.json"
    nodes = list(iter_tana_nodes(path))
    assert len(nodes) == 3
    assert all(isinstance(n, NodeDump) for n in nodes)
    by_id = {n.id: n for n in nodes}
    assert by_id["ROOT_A"].props["name"] == "Home"
    assert by_id["CHILD_B"].children == []
    assert by_id["CHILD_B"].outbound_refs == ["REF_C"]


def test_iter_tana_nodes_store_data_wrapper() -> None:
    path = _FIXTURES / "minimal_store_data.json"
    nodes = list(iter_tana_nodes(path))
    assert len(nodes) == 2
    assert {n.id for n in nodes} == {"WRAP_ROOT", "WRAP_CHILD"}


def test_iter_tana_nodes_rejects_json_load(monkeypatch: pytest.MonkeyPatch) -> None:
    """Streaming path must not call json.load on the export file."""

    def _forbidden_load(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("json.load must not be used for Tana export parsing")

    monkeypatch.setattr(json, "load", _forbidden_load)
    nodes = list(iter_tana_nodes(_FIXTURES / "minimal_direct.json"))
    assert len(nodes) == 3


def test_load_tana_nodes_by_id_index() -> None:
    index = load_tana_nodes_by_id(_FIXTURES / "minimal_direct.json")
    assert set(index) == {"ROOT_A", "CHILD_B", "REF_C"}
    assert index["CHILD_B"].props["created"] == 1734912000000


def test_iter_tana_nodes_skips_invalid_entries(tmp_path: Path) -> None:
    export = tmp_path / "mixed.json"
    export.write_bytes(
        b'{"docs": ['
        b'{"id": "ok", "props": {}, "children": []},'
        b'{"props": {"name": "no id"}},'
        b'"not-a-node"'
        b"]}"
    )
    nodes = list(iter_tana_nodes(export))
    assert len(nodes) == 1
    assert nodes[0].id == "ok"


def test_iter_tana_nodes_large_export_streaming(tmp_path: Path) -> None:
    """Many nodes via generator — no requirement to hold full JSON DOM."""
    count = 1200
    parts = ['{"docs": [']
    for i in range(count):
        if i:
            parts.append(",")
        parts.append(f'{{"id": "N{i}", "props": {{"name": "node {i}"}}, "children": []}}')
    parts.append("]}")
    export = tmp_path / "large.json"
    export.write_text("".join(parts), encoding="utf-8")

    seen = 0
    for node in iter_tana_nodes(export):
        seen += 1
        assert node.id.startswith("N")
    assert seen == count


def test_get_logseq_journal_format_custom_edn(tmp_path: Path) -> None:
    logseq_dir = tmp_path / "logseq"
    logseq_dir.mkdir()
    fixture_text = (_FIXTURES / "config_custom_journal.edn").read_text(encoding="utf-8")
    (logseq_dir / "config.edn").write_text(fixture_text, encoding="utf-8")

    result = get_logseq_journal_format(tmp_path)
    assert result.format_string == "MMM do, yyyy"
    assert result.source == "config.edn"
    assert result.warning is None


def test_get_logseq_journal_format_missing_config(tmp_path: Path) -> None:
    result = get_logseq_journal_format(tmp_path)
    assert result.format_string == DEFAULT_JOURNAL_PAGE_TITLE_FORMAT
    assert result.warning is not None
    assert "not found" in result.warning


def test_get_logseq_journal_format_malformed_edn(tmp_path: Path) -> None:
    logseq_dir = tmp_path / "logseq"
    logseq_dir.mkdir()
    (logseq_dir / "config.edn").write_text("{:broken", encoding="utf-8")

    result = get_logseq_journal_format(tmp_path)
    assert result.format_string == DEFAULT_JOURNAL_PAGE_TITLE_FORMAT
    assert result.warning is not None
    assert "malformed" in result.warning
