"""Safe integer parsing for MCP/CLI JSON tool options."""

from __future__ import annotations

import json
from pathlib import Path

from src.agent.graph_tool_helpers import bounded_int_from_options


def test_bounded_int_from_options_clamps() -> None:
    assert (
        bounded_int_from_options(
            {"limit": "25"},
            "limit",
            default=15,
            minimum=1,
            maximum=100,
        )
        == 25
    )


def test_bounded_int_from_options_rejects_invalid() -> None:
    result = bounded_int_from_options(
        {"limit": "not-a-number"},
        "limit",
        default=15,
        minimum=1,
        maximum=100,
    )
    assert isinstance(result, str)
    assert "Invalid integer" in result


def test_bounded_int_from_options_rejects_bool_false() -> None:
    result = bounded_int_from_options(
        {"limit": False},
        "limit",
        default=15,
        minimum=1,
        maximum=100,
    )
    assert isinstance(result, str)
    assert "Invalid integer" in result


def test_bounded_int_from_options_rejects_bool_true() -> None:
    result = bounded_int_from_options(
        {"limit": True},
        "limit",
        default=15,
        minimum=1,
        maximum=100,
    )
    assert isinstance(result, str)
    assert "Invalid integer" in result


def test_read_subtree_heading_excludes_sibling_sections(tmp_path: Path) -> None:
    from src.agent.graph_tool_helpers import read_subtree_markdown

    block_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    pages = tmp_path / "pages"
    pages.mkdir(parents=True)
    (pages / "Demo.md").write_text(
        f"- Root\n  id:: {block_id}\n  - Section B\n    - b1\n  - Section C\n    - c1\n",
        encoding="utf-8",
    )
    query = json.dumps({"page": "Demo", "block_uuid": block_id, "heading": "Section B"})
    md = read_subtree_markdown(str(tmp_path), query)
    assert "Section B" in md
    assert "b1" in md
    assert "Section C" not in md
    assert "c1" not in md
