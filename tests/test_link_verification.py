"""Tests for structural link verification (#15)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from src.graph.link_verification import (
    LinkRegistryEntry,
    extract_links_from_page,
    flag_block_hygiene_property,
    link_registry_path,
    link_verify_strikes_threshold,
    load_link_registry,
    merge_page_links_into_registry,
    verify_registry_batch,
)

BLOCK = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


@pytest.fixture
def graph_with_page(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "graph"
    pages = root / "pages"
    pages.mkdir(parents=True)
    assets = root / "assets"
    assets.mkdir()
    page = pages / "demo.md"
    page.write_text(
        "\n".join(
            [
                "- Read https://example.com/ok",
                f"  id:: {BLOCK}",
                "- ![diagram](../assets/missing.png)",
                "  id:: bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                "",
            ],
        ),
        encoding="utf-8",
    )
    return root, page


def test_extract_links_from_page(graph_with_page: tuple[Path, Path]) -> None:
    root, page = graph_with_page
    content = page.read_text(encoding="utf-8")
    entries = extract_links_from_page(root, page, content)
    kinds = {(e.kind, e.target) for e in entries}
    assert ("url", "https://example.com/ok") in kinds
    assert any(e.kind == "asset" and "missing.png" in e.target for e in entries)


def test_merge_registry_and_flag_asset(
    graph_with_page: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, page = graph_with_page
    monkeypatch.setenv("MATRYCA_LINK_VERIFY_STRIKES", "1")
    assert link_verify_strikes_threshold() == 1

    merge_page_links_into_registry(root, page, page.read_text(encoding="utf-8"))
    registry = load_link_registry(root)
    assert registry

    asset_key = next(k for k, v in registry.items() if v.kind == "asset")
    entry = registry[asset_key]
    entry.strikes = link_verify_strikes_threshold()

    flagged = flag_block_hygiene_property(
        root,
        entry.page_relpath,
        entry.block_uuid,
        "missing-asset",
    )
    assert flagged
    text = page.read_text(encoding="utf-8")
    assert "missing-asset:: true" in text


@pytest.mark.asyncio
async def test_verify_registry_batch_url_dead(
    graph_with_page: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, page = graph_with_page
    monkeypatch.setenv("MATRYCA_LINK_VERIFY_STRIKES", "1")
    entry = LinkRegistryEntry(
        kind="url",
        target="https://example.com/dead",
        page_relpath="pages/demo.md",
        block_uuid=BLOCK,
    )
    registry = {entry.registry_key(): entry}

    async def fake_head(_client: object, _url: str) -> int:
        return 404

    with patch("src.graph.link_verification._head_url", new=fake_head), patch(
        "src.graph.link_verification.flag_block_hygiene_property",
        return_value=True,
    ) as flag_mock:
        result = await verify_registry_batch(root, registry, batch_size=5)

    assert result.checked == 1
    assert result.dead_urls == 1
    flag_mock.assert_called_once()
    assert link_registry_path(root).is_file()
    assert registry[entry.registry_key()].flagged is True
