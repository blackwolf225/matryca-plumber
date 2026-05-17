"""Async client for Logseq's local HTTP JSON-RPC API."""

from __future__ import annotations

import uuid
from types import TracebackType
from typing import Any

import httpx
from loguru import logger
from pydantic import BaseModel, Field

_DEFAULT_TIMEOUT = httpx.Timeout(30.0)


class JsonRpcRequest(BaseModel):
    """JSON-RPC 2.0 request envelope."""

    jsonrpc: str = Field(default="2.0")
    id: int | str
    method: str
    params: list[Any] | dict[str, Any] = Field(default_factory=lambda: [])


class LogseqClient:
    """Thin async wrapper around the Logseq local HTTP API.

    The API listens on a configurable base URL (commonly ``http://localhost:12315``)
    and expects a Bearer token in ``Authorization`` for authenticated calls.
    """

    def __init__(
        self,
        api_url: str,
        token: str,
        *,
        timeout: httpx.Timeout | None = None,
    ) -> None:
        """Create a client bound to a Logseq instance.

        Args:
            api_url: Base URL of the Logseq HTTP API (no trailing slash required).
            token: API token used as ``Bearer`` credentials.
            timeout: Optional HTTP client timeout. Defaults to 30 seconds.
        """
        base = api_url.rstrip("/") + "/"
        self._timeout = timeout or _DEFAULT_TIMEOUT
        self._client = httpx.AsyncClient(
            base_url=base,
            headers={"Authorization": f"Bearer {token}"},
            timeout=self._timeout,
        )

    async def aclose(self) -> None:
        """Release underlying HTTP resources."""
        await self._client.aclose()

    async def __aenter__(self) -> LogseqClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def _post_json_rpc(self, payload: JsonRpcRequest) -> dict[str, Any]:
        """Send a single JSON-RPC request and return the parsed JSON object.

        Raises:
            httpx.HTTPError: When the transport fails.
            ValueError: When the response body is not a JSON object.
        """
        body = payload.model_dump()
        response = await self._client.post("", json=body)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            msg = "Logseq API returned a non-object JSON body"
            raise ValueError(msg)
        return data

    async def append_block(
        self,
        parent_uuid: str,
        content: str,
        properties: dict[str, str],
    ) -> str:
        """Append a child block beneath ``parent_uuid`` via the Logseq editor API.

        This method is a **stub** for ``logseq.Editor.insertBlock``-style JSON-RPC
        calls. Until the real RPC is wired, it returns a fresh UUID so callers can
        chain nested inserts using Logseq's actual parent UUID semantics.

        Args:
            parent_uuid: UUID of the parent Logseq block (string form).
            content: Markdown / outliner text for the new block body.
            properties: Block properties (e.g. ``{"id": "<uuid>"}``) as string pairs.

        Returns:
            Synthetic UUID string for the created block (stub behavior).

        Raises:
            httpx.HTTPError: When the real implementation performs HTTP and transport fails.
        """
        new_uuid = str(uuid.uuid4())
        logger.bind(
            parent_uuid=parent_uuid,
            content_len=len(content),
            new_block_uuid=new_uuid,
            props=len(properties),
        ).info("append_block stub: returning synthetic block UUID (no HTTP insert yet)")
        return new_uuid
