"""Tests for Telos & Identity config layer and store_fact MCP tool."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from src.agent.llm_client import InstructorLLMClient
from src.agent.mcp_tool_guard import guard_mcp_tool
from src.agent.memory_tools import dispatch_store_fact
from src.daemon.ast_cache import clear_graph_ast_cache, get_graph_ast_cache
from src.daemon.config_layer import (
    TELOS_HEADING,
    append_identity_to_mcp_payload,
    clear_identity_config_stores,
    get_identity_store,
    inject_identity_into_system_prompt,
    resolve_identity_read_page_title,
)


@pytest.fixture(autouse=True)
def _clear_identity_caches() -> Iterator[None]:
    clear_graph_ast_cache()
    clear_identity_config_stores()
    yield
    clear_graph_ast_cache()
    clear_identity_config_stores()


def _write_config_page(pages: Path, name: str, body: str) -> Path:
    path = pages / name
    path.write_text(body, encoding="utf-8")
    return path


def test_extract_telos_and_constraints_from_matryca_config_page(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pages = tmp_path / "pages"
    pages.mkdir()
    _write_config_page(
        pages,
        "matryca___config.md",
        f"- # {TELOS_HEADING}\n  - Researcher focused on case law\n"
        f"- # AI Constraints\n  - Prefer bullet lists\n  - Never invent citations\n",
    )
    monkeypatch.setenv("LOGSEQ_GRAPH_PATH", str(tmp_path))

    get_graph_ast_cache(tmp_path).bootstrap()
    cfg = get_identity_store(tmp_path).get()

    assert cfg.source_page == "matryca/config"
    assert "case law" in cfg.telos
    assert "bullet lists" in cfg.constraints
    assert "Never invent citations" in cfg.constraints


def test_fallback_matryca_config_page_title(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pages = tmp_path / "pages"
    pages.mkdir()
    _write_config_page(
        pages,
        "matryca-config.md",
        f"- # {TELOS_HEADING}\n  - Lawyer\n- # AI Constraints\n  - Formal tone\n",
    )
    monkeypatch.setenv("LOGSEQ_GRAPH_PATH", str(tmp_path))

    assert resolve_identity_read_page_title(tmp_path) == "matryca-config"
    cfg = get_identity_store(tmp_path).get()
    assert cfg.telos.strip() == "Lawyer"
    assert "Formal tone" in cfg.constraints


def test_reload_on_apply_file_event(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pages = tmp_path / "pages"
    pages.mkdir()
    path = _write_config_page(
        pages,
        "matryca-config.md",
        f"- # {TELOS_HEADING}\n  - Version one\n- # AI Constraints\n",
    )
    monkeypatch.setenv("LOGSEQ_GRAPH_PATH", str(tmp_path))
    cache = get_graph_ast_cache(tmp_path)
    cache.bootstrap()
    store = get_identity_store(tmp_path)
    assert "Version one" in store.get().telos

    path.write_text(
        f"- # {TELOS_HEADING}\n  - Version two\n- # AI Constraints\n",
        encoding="utf-8",
    )
    cache.apply_file_event(path, "modified")
    store.reload_if_stale(force=True)
    assert "Version two" in store.get().telos


def test_system_prompt_contains_persona(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pages = tmp_path / "pages"
    pages.mkdir()
    _write_config_page(
        pages,
        "matryca-config.md",
        f"- # {TELOS_HEADING}\n  - Maritime engineer\n- # AI Constraints\n  - Use SI units\n",
    )
    monkeypatch.setenv("LOGSEQ_GRAPH_PATH", str(tmp_path))
    get_graph_ast_cache(tmp_path).bootstrap()

    client = InstructorLLMClient(api_key="test", base_url="http://127.0.0.1:9", model="test")
    messages = client._completion_messages(  # noqa: SLF001
        system_prompt="Base instructions.",
        prompt="Hello",
        stateless=True,
    )
    system = messages[0]["content"]
    assert "Maritime engineer" in system
    assert "SI units" in system
    assert "[MATRYCA IDENTITY — Telos]" in system


def test_mcp_output_includes_identity_footer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pages = tmp_path / "pages"
    pages.mkdir()
    _write_config_page(
        pages,
        "matryca-config.md",
        f"- # {TELOS_HEADING}\n  - Pilot\n- # AI Constraints\n  - Be concise\n",
    )
    monkeypatch.setenv("LOGSEQ_GRAPH_PATH", str(tmp_path))
    get_graph_ast_cache(tmp_path).bootstrap()

    out = append_identity_to_mcp_payload("tool body")
    assert isinstance(out, str)
    assert "Pilot" in out
    assert "matryca_identity" in out


@pytest.mark.asyncio
async def test_store_fact_mcp_tool_injects_safely(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pages = tmp_path / "pages"
    pages.mkdir()
    monkeypatch.setenv("LOGSEQ_GRAPH_PATH", str(tmp_path))

    result = await dispatch_store_fact("Always cite block UUIDs when editing.")
    assert result["ok"] is True
    assert result["page"] == "matryca-config"

    config_path = pages / "matryca-config.md"
    assert config_path.is_file()
    text = config_path.read_text(encoding="utf-8")
    assert "- # Telos" in text
    assert "- # AI Constraints" in text
    assert "Always cite block UUIDs when editing." in text
    lines = text.splitlines()
    constraint_idx = next(i for i, ln in enumerate(lines) if "AI Constraints" in ln)
    fact_idx = next(i for i, ln in enumerate(lines) if "Always cite block UUIDs" in ln)
    assert fact_idx > constraint_idx
    assert lines[fact_idx].startswith("  - ")

    get_graph_ast_cache(tmp_path).bootstrap()
    cfg = get_identity_store(tmp_path).get()
    assert "Always cite block UUIDs" in cfg.constraints


@pytest.mark.asyncio
async def test_guard_mcp_tool_skips_identity_on_store_fact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pages = tmp_path / "pages"
    pages.mkdir()
    _write_config_page(
        pages,
        "matryca-config.md",
        f"- # {TELOS_HEADING}\n  - X\n- # AI Constraints\n  - Y\n",
    )
    monkeypatch.setenv("LOGSEQ_GRAPH_PATH", str(tmp_path))
    get_graph_ast_cache(tmp_path).bootstrap()

    @guard_mcp_tool
    async def store_fact(fact: str) -> dict[str, object]:
        return {"ok": True, "fact": fact}

    out = await store_fact("sample")
    assert isinstance(out, dict)
    assert "identity_context" not in out


def test_inject_identity_is_idempotent() -> None:
    once = inject_identity_into_system_prompt(
        "Base\n\n[MATRYCA IDENTITY — Telos]\nfoo",
    )
    assert once.count("[MATRYCA IDENTITY — Telos]") == 1
