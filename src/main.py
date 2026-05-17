"""Application entrypoint: load config, wire Logseq, and run the MCP server (stdio)."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession

from .agent.mcp_server import MatrycaMCPServer
from .bridge.logseq_client import LogseqClient


@dataclass(frozen=True, slots=True)
class AppContext:
    """Dependencies available for the MCP server lifetime."""

    bridge: MatrycaMCPServer


@asynccontextmanager
async def app_lifespan(_server: FastMCP) -> AsyncIterator[AppContext]:
    """Create the Logseq client and MCP bridge for the stdio session lifetime.

    Args:
        _server: FastMCP instance (unused; reserved for future hooks).

    Yields:
        Application context holding the live :class:`MatrycaMCPServer`.

    Raises:
        ValueError: If ``LOGSEQ_API_TOKEN`` is unset (required for authenticated calls).
    """
    load_dotenv()
    api_url = os.environ.get("LOGSEQ_API_URL", "http://localhost:12315").rstrip("/")
    token = os.environ.get("LOGSEQ_API_TOKEN", "").strip()
    if not token:
        msg = (
            "LOGSEQ_API_TOKEN is not set. Add it to your environment or `.env` file "
            "before starting the MCP server."
        )
        raise ValueError(msg)

    client = LogseqClient(api_url=api_url, token=token)
    bridge = MatrycaMCPServer(client=client)
    logger.bind(api_url=api_url).info("Matryca MCP lifespan started (stdio)")
    try:
        yield AppContext(bridge=bridge)
    finally:
        await client.aclose()
        logger.info("Matryca MCP lifespan stopped")


mcp = FastMCP("matryca-logseq-llm-wiki", lifespan=app_lifespan)


@mcp.tool()
async def write_logseq_outline(
    outline: dict[str, Any],
    parent_block_uuid: str,
    ctx: Context[ServerSession, AppContext],
) -> list[str]:
    """Create blocks from a nested outline under ``parent_block_uuid`` (parent-first order).

    Args:
        outline: Mapping compatible with :class:`~src.agent.mcp_server.OutlineNode`.
        parent_block_uuid: Existing Logseq block UUID to attach the root node under.
        ctx: Injected MCP context with lifespan-bound services.

    Returns:
        DFS-ordered list of UUID strings for every created block.

    """
    bridge = ctx.request_context.lifespan_context.bridge
    return await bridge.write_logseq_outline(
        outline,
        parent_block_uuid=parent_block_uuid,
    )


async def _run_stdio_server() -> None:
    """Run the FastMCP stdio transport on the current event loop."""
    await mcp.run_stdio_async()


def main() -> None:
    """CLI entrypoint for ``python -m src.main``."""
    asyncio.run(_run_stdio_server())


if __name__ == "__main__":
    main()
