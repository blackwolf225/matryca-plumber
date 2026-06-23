"""End-to-end tests for the Tana import orchestrator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from src.agent.tana_import import run_tana_import
from src.graph.markdown_blocks import graph_safe_page_path

_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "tana"


def _prepare_vault(tmp_path: Path) -> Path:
    graph_root = tmp_path / "vault"
    (graph_root / "pages").mkdir(parents=True)
    (graph_root / "journals").mkdir()
    return graph_root


def test_run_tana_import_missing_export_returns_error(tmp_path: Path) -> None:
    graph_root = _prepare_vault(tmp_path)
    missing = tmp_path / "missing.json"

    result = run_tana_import(missing, apply=False, graph_root=graph_root)

    assert result.ok is False
    assert "not found" in (result.error or "").casefold()


def test_run_tana_import_dry_run_entity_graph(tmp_path: Path) -> None:
    graph_root = _prepare_vault(tmp_path)
    export = _FIXTURES / "entity_graph.json"

    result = run_tana_import(export, apply=False, graph_root=graph_root)

    assert result.ok is True
    assert result.apply is False
    assert result.pages_planned >= 2
    assert result.write["pages_created"]
    assert not list(graph_root.rglob("*.md"))


def test_run_tana_import_apply_writes_entity_pages(tmp_path: Path) -> None:
    graph_root = _prepare_vault(tmp_path)
    export = _FIXTURES / "entity_graph.json"

    result = run_tana_import(export, apply=True, graph_root=graph_root)

    assert result.ok is True
    assert result.apply is True
    project_path = graph_safe_page_path(graph_root, "Tana/project/My project")
    ledger_path = graph_safe_page_path(graph_root, "Tana/Import Log")

    assert project_path.is_file()
    assert ledger_path.is_file()
    assert "Tana/project/My project" in result.write["pages_created"]
    project_text = project_path.read_text(encoding="utf-8")
    assert "My project" in project_text
    assert "tana-id:: TAGGED" in project_text
    assert result.write["blocks_written"] >= 2


def test_run_tana_import_resolves_in_flight_wikilinks(tmp_path: Path) -> None:
    graph_root = _prepare_vault(tmp_path)
    export = tmp_path / "cross_ref.json"
    export.write_text(
        json.dumps(
            {
                "docs": [
                    {
                        "id": "ENT_A",
                        "props": {"name": "Alpha", "_flags": 1},
                        "children": ["CHILD"],
                    },
                    {
                        "id": "CHILD",
                        "props": {"name": "See [[Beta]]"},
                        "children": [],
                    },
                    {
                        "id": "ENT_B",
                        "props": {"name": "Beta", "_flags": 1},
                        "children": [],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    result = run_tana_import(export, apply=True, graph_root=graph_root)

    assert result.ok is True
    assert result.link_stats["in_flight_resolved"] >= 1
    alpha_path = graph_safe_page_path(graph_root, "Tana/Alpha")
    alpha_text = alpha_path.read_text(encoding="utf-8")
    assert "[[Tana/Beta]]" in alpha_text
    assert "[[Beta]]" not in alpha_text


def test_run_tana_import_idempotent_reimport_skips_duplicates(tmp_path: Path) -> None:
    graph_root = _prepare_vault(tmp_path)
    export = _FIXTURES / "entity_graph.json"

    first = run_tana_import(export, apply=True, graph_root=graph_root)
    second = run_tana_import(export, apply=True, graph_root=graph_root)

    assert first.ok is True
    assert second.ok is True
    assert second.write["skipped_duplicates"] >= len(first.write["pages_created"])


def test_run_tana_import_requires_graph_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOGSEQ_GRAPH_PATH", raising=False)
    export = _FIXTURES / "entity_graph.json"

    result = run_tana_import(export, apply=False)

    assert result.ok is False
    assert "LOGSEQ_GRAPH_PATH" in (result.error or "")
