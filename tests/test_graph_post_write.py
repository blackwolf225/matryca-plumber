"""Tests for graph-local post-write port (#134)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from src.graph.markdown_blocks import atomic_write_bytes
from src.graph.post_write import (
    PageWrittenEvent,
    clear_page_written_handlers,
    emit_page_written,
    register_page_written_handler,
)


@pytest.fixture
def _isolate_page_written_handlers() -> Iterator[None]:
    clear_page_written_handlers()
    yield
    clear_page_written_handlers()
    from src.daemon.ast_cache import clear_graph_ast_cache

    clear_graph_ast_cache()


def test_markdown_blocks_has_no_daemon_import() -> None:
    source = Path("src/graph/markdown_blocks.py").read_text(encoding="utf-8")
    assert "daemon" not in source


def test_graph_coupling_slice134_reversed() -> None:
    """#134 follow-up: graph read/write paths no longer import daemon orchestration."""
    checks = {
        "src/graph/markdown_blocks.py": ("daemon", "maintenance_daemon"),
        "src/graph/block_ref_lint.py": ("..daemon", "maintenance_daemon"),
        "src/graph/dashboard.py": ("..daemon", "maintenance_daemon"),
        "src/graph/bootstrap_status.py": ("maintenance_daemon",),
    }
    for rel, forbidden in checks.items():
        text = Path(rel).read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text, f"{rel} still references {needle!r}"


def test_emit_page_written_notifies_handlers(
    tmp_path: Path,
    _isolate_page_written_handlers: None,
) -> None:
    clear_page_written_handlers()
    seen: list[PageWrittenEvent] = []
    register_page_written_handler(lambda event: seen.append(event))

    page = tmp_path / "pages" / "Note.md"
    page.parent.mkdir(parents=True)
    atomic_write_bytes(
        page,
        b"- hello\n",
        graph_root=tmp_path,
        robot_commit_summary="robot note",
    )

    assert len(seen) == 1
    assert seen[0].path == page.resolve()
    assert seen[0].graph_root == tmp_path.resolve()
    assert seen[0].summary == "robot note"


def test_handler_failure_does_not_abort_emit(
    tmp_path: Path,
    _isolate_page_written_handlers: None,
) -> None:
    clear_page_written_handlers()
    ok: list[str] = []

    def _boom(_event: PageWrittenEvent) -> None:
        raise RuntimeError("handler failed")

    register_page_written_handler(_boom)
    register_page_written_handler(lambda _event: ok.append("ok"))

    emit_page_written(
        graph_root=tmp_path,
        path=tmp_path / "pages" / "X.md",
        summary=None,
    )

    assert ok == ["ok"]
