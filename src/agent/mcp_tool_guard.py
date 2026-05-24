"""Outer error boundaries for MCP tool handlers (no raw tracebacks to clients)."""

from __future__ import annotations

import functools
import inspect
from collections.abc import Awaitable, Callable
from typing import Any, cast

from loguru import logger

from ..graph.path_sandbox import PathTraversalSecurityError


def _tool_returns_text(fn: Callable[..., Any]) -> bool:
    ann = inspect.signature(fn).return_annotation
    if ann is inspect.Signature.empty:
        return False
    if ann is str:
        return True
    return isinstance(ann, str) and ann.split("[", 1)[0].strip() == "str"


def format_tool_error(
    exc: Exception,
    *,
    as_text: bool,
    code: str = "tool_error",
    hint: str = "Check inputs and environment, then retry.",
) -> str | dict[str, Any]:
    """Map an exception to a concise MCP tool response."""
    message = str(exc).strip() or exc.__class__.__name__
    if as_text:
        return f"Tool failed: {message}"
    return {
        "ok": False,
        "code": code,
        "error": message,
        "hint": hint,
    }


def guard_mcp_tool[F: Callable[..., Awaitable[Any]]](fn: F) -> F:
    """Catch unhandled domain errors and return LLM-safe tool output."""

    returns_text = _tool_returns_text(fn)

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await fn(*args, **kwargs)
        except PathTraversalSecurityError as exc:
            logger.bind(tool=fn.__name__).warning("MCP tool security error: {}", exc)
            return format_tool_error(
                exc,
                as_text=returns_text,
                code="security_violation",
                hint="Stay within LOGSEQ_GRAPH_PATH and retry with a valid page reference.",
            )
        except ValueError as exc:
            logger.bind(tool=fn.__name__).warning("MCP tool validation error: {}", exc)
            return format_tool_error(exc, as_text=returns_text)
        except (OSError, RuntimeError, FileNotFoundError, ImportError) as exc:
            logger.bind(tool=fn.__name__).warning("MCP tool domain error: {}", exc)
            return format_tool_error(exc, as_text=returns_text)
        except Exception as exc:
            logger.bind(tool=fn.__name__).exception("Unhandled MCP tool error")
            return format_tool_error(exc, as_text=returns_text)

    return cast(F, wrapper)


__all__ = ["format_tool_error", "guard_mcp_tool"]
