"""Tests for outline security gate."""

from __future__ import annotations

import pytest
from src.agent.quality_gate import advanced_query_security_violations, outline_security_violations


def test_outline_security_flags_token_property() -> None:
    outline = {
        "text": "x",
        "properties": {"token::": "abc"},
        "children": [],
    }
    assert outline_security_violations(outline)


def test_clean_outline_has_no_violations() -> None:
    outline = {"text": "Safe note", "properties": {"tags::": "[[x]]"}, "children": []}
    assert not outline_security_violations(outline)


def test_advanced_query_security_flags_sk_pattern() -> None:
    bad = '{:query [:find ?a :where [?a :block/content "sk-12345678901234567890123456789012"]]}'
    assert advanced_query_security_violations(bad)


@pytest.mark.asyncio
async def test_write_entity_includes_alias_routing_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.agent.mcp_server import MatrycaMCPServer
    from src.bridge.logseq_client import LogseqClient

    client = LogseqClient(api_url="http://127.0.0.1:9", token="t")

    async def fake_append(
        parent_uuid: str,
        content: str,
        properties: dict[str, str],
    ) -> str:
        return "uuid-1"

    monkeypatch.setattr(client, "append_block", fake_append)
    monkeypatch.setenv("LOGSEQ_GRAPH_PATH", "")

    server = MatrycaMCPServer(client=client)
    outline = {
        "text": "Entity root",
        "page_type": "entity",
        "entity_type": "tool",
        "children": [],
    }
    out = await server.write_logseq_outline(outline, parent_block_uuid="root")
    assert "resolve_logseq_entity" in out["routing_hint"]


@pytest.mark.asyncio
async def test_write_rejects_outline_with_secret() -> None:
    from src.agent.mcp_server import MatrycaMCPServer
    from src.bridge.logseq_client import LogseqClient

    client = LogseqClient(api_url="http://127.0.0.1:9", token="t")
    server = MatrycaMCPServer(client=client)
    bad = {"text": "leak", "properties": {"password::": "x"}, "children": []}
    with pytest.raises(ValueError, match="credential-like"):
        await server.write_logseq_outline(bad, parent_block_uuid="root")
