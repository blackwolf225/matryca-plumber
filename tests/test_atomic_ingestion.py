"""Tests for atomic document ingestion (Phase 2)."""

from __future__ import annotations

import os
import re
from datetime import date
from pathlib import Path

import pytest
from src.agent.ingestion import (
    INGEST_ENV_KEY,
    _parse_markdown_to_page,
    dispatch_ingest_document,
    process_ingestion,
    resolve_ingest_destination_page_title,
)
from src.graph.page_path import page_title_to_filename


def test_resolve_ingest_destination_daily_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(INGEST_ENV_KEY, raising=False)
    title = resolve_ingest_destination_page_title(as_of=date(2026, 5, 31))
    assert title == "Ingest/2026-05-31"
    assert page_title_to_filename(title) == "Ingest___2026-05-31.md"


def test_resolve_ingest_destination_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(INGEST_ENV_KEY, "AI_Inbox")
    assert resolve_ingest_destination_page_title() == "AI_Inbox"


def test_parse_markdown_uses_os_temp_not_pages(tmp_path: Path) -> None:
    pages = tmp_path / "pages"
    pages.mkdir()
    before = set(pages.iterdir())

    page = _parse_markdown_to_page("- Alpha\n  - Beta\n")
    assert page.root_nodes
    after = set(pages.iterdir())
    assert before == after


def test_process_ingestion_writes_destination_log_glossary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pages = tmp_path / "pages"
    pages.mkdir()
    monkeypatch.setenv("LOGSEQ_GRAPH_PATH", str(tmp_path))
    monkeypatch.delenv(INGEST_ENV_KEY, raising=False)

    raw = (
        "- Meeting notes about #legal-tech\n"
        "  - Follow up with Acme Corp\n"
        "  - Review Contract-Law checklist\n"
    )
    result = process_ingestion(
        tmp_path,
        "Weekly sync",
        raw,
        as_of=date(2026, 5, 31),
    )

    assert result.ok
    ingest_path = pages / "Ingest___2026-05-31.md"
    assert ingest_path.is_file()
    ingest_text = ingest_path.read_text(encoding="utf-8")
    assert "Ingested: **Weekly sync**" in ingest_text
    assert "id::" in ingest_text
    assert "Meeting notes" in ingest_text
    assert len(result.block_uuids) >= 3
    uuid_re = re.compile(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        re.IGNORECASE,
    )
    for block_id in result.block_uuids:
        assert uuid_re.match(block_id)

    log_path = pages / "LOG.md"
    assert log_path.is_file()
    log_text = log_path.read_text(encoding="utf-8")
    assert "Weekly sync" in log_text
    assert "Generated" in log_text
    assert result.block_uuids[0] in log_text

    glossary_path = pages / "GLOSSARY.md"
    assert glossary_path.is_file()
    glossary_text = glossary_path.read_text(encoding="utf-8")
    assert "legal-tech" in glossary_text or "Legal-Tech" in glossary_text
    assert "{{embed ((" in glossary_text


def test_process_ingestion_respects_fixed_inbox_page(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pages = tmp_path / "pages"
    pages.mkdir()
    monkeypatch.setenv("LOGSEQ_GRAPH_PATH", str(tmp_path))
    monkeypatch.setenv(INGEST_ENV_KEY, "AI_Inbox")

    process_ingestion(tmp_path, "Email dump", "- One bullet\n", as_of=date(2026, 1, 1))

    assert (pages / "AI_Inbox.md").is_file()
    assert not (pages / "Ingest___2026-01-01.md").exists()


def test_process_ingestion_rejects_secrets(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="forbidden secret"):
        process_ingestion(
            tmp_path,
            "Leak",
            "api_key=sk-1234567890123456789012345678901234567890",
        )


@pytest.mark.asyncio
async def test_dispatch_ingest_document_requires_graph(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LOGSEQ_GRAPH_PATH", raising=False)
    with pytest.raises(ValueError, match="LOGSEQ_GRAPH_PATH"):
        await dispatch_ingest_document("x", "- y\n")


def test_tempfile_unlinked_after_parse(monkeypatch: pytest.MonkeyPatch) -> None:
    unlinked: list[str] = []
    real_unlink = os.unlink

    def track_unlink(path: str | bytes, *args: object, **kwargs: object) -> None:
        unlinked.append(str(path))
        real_unlink(path, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(os, "unlink", track_unlink)
    _parse_markdown_to_page("- Solo\n")
    assert unlinked
    assert str(unlinked[0]).endswith(".md")
    assert not os.path.exists(unlinked[0])
