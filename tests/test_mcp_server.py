"""Tests for MCP server models and outline validation."""

from __future__ import annotations

from typing import Any

import pytest
from src.agent.mcp_server import MatrycaMCPServer, OutlineNode
from src.bridge.logseq_client import LogseqClient


@pytest.mark.asyncio
async def test_outline_node_validates_nested_hierarchy() -> None:
    """``OutlineNode`` should accept nested JSON and preserve parent/child structure."""
    payload: dict[str, object] = {
        "text": "Root thesis",
        "properties": {"tags::": "[[AI]]"},
        "children": [
            {
                "text": "Supporting claim",
                "children": [{"text": "Evidence leaf", "properties": {}, "children": []}],
            },
        ],
    }
    node = OutlineNode.model_validate(payload)
    assert node.text == "Root thesis"
    assert len(node.children) == 1
    assert node.children[0].text == "Supporting claim"
    assert node.children[0].children[0].text == "Evidence leaf"


@pytest.mark.asyncio
async def test_write_logseq_outline_chains_parent_uuids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each child append must use the UUID returned from its parent's ``append_block``."""
    client = LogseqClient(api_url="http://127.0.0.1:9", token="test-token")
    calls: list[tuple[str, str]] = []

    async def fake_append(
        parent_uuid: str,
        content: str,
        properties: dict[str, str],
    ) -> str:
        calls.append((parent_uuid, content))
        return f"uuid-{len(calls)}"

    monkeypatch.setattr(client, "append_block", fake_append)

    server = MatrycaMCPServer(client=client)
    outline: dict[str, Any] = {
        "text": "Root",
        "children": [{"text": "Child", "children": [{"text": "Grandchild"}]}],
    }
    uuids = await server.write_logseq_outline(outline, parent_block_uuid="page-root")

    assert uuids == ["uuid-1", "uuid-2", "uuid-3"]
    assert calls[0] == ("page-root", "Root")
    assert calls[1] == ("uuid-1", "Child")
    assert calls[2] == ("uuid-2", "Grandchild")
