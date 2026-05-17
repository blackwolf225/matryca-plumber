"""Agent-facing MCP server scaffolding (tools bridge to Logseq)."""

from __future__ import annotations

from typing import Any, cast

from loguru import logger
from pydantic import BaseModel, Field, field_validator

from ..bridge.logseq_client import LogseqClient


class OutlineNode(BaseModel):
    """Hierarchical outline node as accepted by agent tools (JSON-serializable)."""

    text: str = Field(..., description="Block text (Logseq outliner / Markdown body).")
    properties: dict[str, str] = Field(
        default_factory=dict,
        description="Optional Logseq-style properties (string keys/values).",
    )
    children: list[OutlineNode] = Field(default_factory=list)

    @field_validator("children", mode="before")
    @classmethod
    def _empty_children(cls, value: Any) -> list[Any]:  # noqa: ANN401
        """Treat ``null`` / missing children as an empty list."""
        if value is None:
            return []
        return cast(list[Any], value)


class MatrycaMCPServer:
    """MCP-oriented bridge: validates tool payloads and drives :class:`LogseqClient`."""

    def __init__(self, client: LogseqClient | None = None) -> None:
        """Store the Logseq client used for async block creation.

        Args:
            client: Live Logseq API client; required for :meth:`write_logseq_outline`.
        """
        self._client = client

    async def write_logseq_outline(
        self,
        outline: dict[str, Any],
        *,
        parent_block_uuid: str,
    ) -> list[str]:
        """Create blocks depth-first, awaiting each parent UUID before writing children.

        Args:
            outline: Nested mapping matching :class:`OutlineNode`
                (``text`` / ``properties`` / ``children``).
            parent_block_uuid: Existing Logseq block UUID to attach the root node under.

        Returns:
            DFS-ordered list of UUID strings returned by :meth:`LogseqClient.append_block`
            for each created block.

        Raises:
            ValueError: If no :class:`LogseqClient` was configured on this server.
        """
        client = self._client
        if client is None:
            msg = "write_logseq_outline requires a configured LogseqClient"
            raise ValueError(msg)

        root = OutlineNode.model_validate(outline)
        created_ids: list[str] = []

        async def walk(node: OutlineNode, parent_uuid: str) -> None:
            new_uuid = await client.append_block(
                parent_uuid,
                node.text,
                dict(node.properties),
            )
            created_ids.append(new_uuid)
            for child in node.children:
                await walk(child, new_uuid)

        await walk(root, parent_block_uuid)
        logger.bind(
            blocks=len(created_ids),
            root_parent=parent_block_uuid,
        ).info("Applied Logseq outline with parent-chained UUIDs")
        return created_ids


__all__ = ["MatrycaMCPServer", "OutlineNode"]
