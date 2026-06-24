"""Tests for Tana import disk writes (dry-run, idempotency, OCC path)."""

from __future__ import annotations

from pathlib import Path

import pytest
from src.agent.importers.tana.convert import ConvertedPagePlan, TanaConvertResult
from src.agent.importers.tana.link import TanaLinkResult
from src.agent.importers.tana.provenance import PROP_TANA_ID
from src.agent.importers.tana.write import (
    TANA_LEDGER_PAGE,
    scan_existing_tana_ids,
    write_tana_import,
)
from src.agent.outline_models import OutlineNode
from src.graph.markdown_blocks import graph_safe_page_path


def _linked_page(
    *,
    page_title: str = "Tana/Demo",
    tana_id: str = "ENT-1",
    block_text: str = "Hello from Tana",
) -> TanaLinkResult:
    return TanaLinkResult(
        convert_result=TanaConvertResult(
            pages=[
                ConvertedPagePlan(
                    page_title=page_title,
                    page_properties={PROP_TANA_ID: tana_id, "tags": "tana-import"},
                    outline_roots=[
                        OutlineNode(
                            text=block_text,
                            properties={PROP_TANA_ID: tana_id},
                        )
                    ],
                )
            ]
        )
    )


def test_dry_run_does_not_touch_filesystem(tmp_path: Path) -> None:
    graph_root = tmp_path / "vault"
    graph_root.mkdir()
    (graph_root / "pages").mkdir()

    report = write_tana_import(_linked_page(), graph_root, apply=False, export_file="mini.json")

    assert report.apply is False
    assert report.pages_created == ["Tana/Demo"]
    assert report.blocks_written == 1
    assert report.skipped_duplicates == 0
    assert not any(graph_root.rglob("*.md"))


def test_apply_creates_page_and_ledger(tmp_path: Path) -> None:
    graph_root = tmp_path / "vault"
    graph_root.mkdir()

    report = write_tana_import(_linked_page(), graph_root, apply=True, export_file="mini.json")

    page_path = graph_safe_page_path(graph_root, "Tana/Demo")
    ledger_path = graph_safe_page_path(graph_root, TANA_LEDGER_PAGE)

    assert report.apply is True
    assert page_path.is_file()
    assert ledger_path.is_file()
    text = page_path.read_text(encoding="utf-8")
    assert "Hello from Tana" in text
    assert "tana-id:: ENT-1" in text
    assert "id::" in text
    assert "made-by:: matryca plumber" in text
    ledger = ledger_path.read_text(encoding="utf-8")
    assert "mini.json" in ledger
    assert "pages_created:: 1" in ledger


def test_scan_existing_tana_ids_streams_multiple_pages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pre-import scan must stream line-by-line, not load full page bodies."""
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages"
    pages.mkdir(parents=True)
    journals = graph_root / "journals"
    journals.mkdir(parents=True)

    (pages / "Alpha.md").write_text("- alpha\n  tana-id:: ID-A\n", encoding="utf-8")
    (pages / "Beta.md").write_text("- beta\n  tana-id:: ID-B\n", encoding="utf-8")
    (journals / "2026_01_01.md").write_text("- journal\n  tana-id:: ID-J\n", encoding="utf-8")

    def fail_full_page_read(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("scan_existing_tana_ids must not load full page text")

    monkeypatch.setattr(
        "src.agent.importers.tana.write.read_graph_file_text",
        fail_full_page_read,
    )

    existing = scan_existing_tana_ids(graph_root)
    assert existing == {"ID-A", "ID-B", "ID-J"}


def test_existing_tana_id_skips_page_write(tmp_path: Path) -> None:
    graph_root = tmp_path / "vault"
    pages = graph_root / "pages" / "Existing.md"
    pages.parent.mkdir(parents=True)
    pages.write_text("- prior import\n  tana-id:: ENT-1\n  id:: abc\n", encoding="utf-8")

    existing = scan_existing_tana_ids(graph_root)
    assert "ENT-1" in existing

    report = write_tana_import(
        _linked_page(),
        graph_root,
        apply=True,
        export_file="mini.json",
        existing_tana_ids=existing,
    )

    assert report.skipped_duplicates == 1
    assert report.pages_created == []
    assert report.blocks_written == 0
    assert not graph_safe_page_path(graph_root, "Tana/Demo").exists()


def test_child_block_skipped_when_tana_id_exists(tmp_path: Path) -> None:
    graph_root = tmp_path / "vault"
    graph_root.mkdir()

    linked = TanaLinkResult(
        convert_result=TanaConvertResult(
            pages=[
                ConvertedPagePlan(
                    page_title="Tana/Parent",
                    page_properties={PROP_TANA_ID: "PARENT"},
                    outline_roots=[
                        OutlineNode(
                            text="Parent block",
                            properties={PROP_TANA_ID: "PARENT"},
                            children=[
                                OutlineNode(
                                    text="Child block",
                                    properties={PROP_TANA_ID: "CHILD-KNOWN"},
                                )
                            ],
                        )
                    ],
                )
            ]
        )
    )

    report = write_tana_import(
        linked,
        graph_root,
        apply=True,
        existing_tana_ids={"CHILD-KNOWN"},
    )

    assert report.pages_created == ["Tana/Parent"]
    assert report.skipped_duplicates == 1
    text = graph_safe_page_path(graph_root, "Tana/Parent").read_text(encoding="utf-8")
    assert "Parent block" in text
    assert "Child block" not in text


def test_write_report_json_shape(tmp_path: Path) -> None:
    graph_root = tmp_path / "vault"
    graph_root.mkdir()

    report = write_tana_import(_linked_page(), graph_root, apply=False)
    payload = report.to_dict()

    assert payload["apply"] is False
    assert payload["pages_created"] == ["Tana/Demo"]
    assert "skipped_duplicates" in payload
    assert TANA_LEDGER_PAGE == "Tana/Import Log"
