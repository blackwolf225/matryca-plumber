"""Machine-readable L1/L2 routing hints appended to MCP tool output."""

from __future__ import annotations

from enum import StrEnum


class RoutingHint(StrEnum):
    """Stable routing marker values embedded in ``<!-- matryca_routing: hint=... -->`` comments."""

    L1_CANDIDATE = "L1_candidate"
    L2_DEFAULT = "L2_default"
    L2_GRAPH_APPEND = "L2_graph_append"
    RESOLVE_ENTITY = "call_search_graph_resolve_entity_for_entities"


def format_routing_comment(hint: RoutingHint) -> str:
    """Serialize one routing hint as an HTML comment for agent parsers."""
    return f"<!-- matryca_routing: hint={hint.value} -->"


def append_read_page_routing_hint(body: str) -> str:
    """Append an HTML comment agents can parse without affecting Logseq rendering."""
    stripped = body.strip()
    if not stripped:
        return body
    if stripped.startswith("LOGSEQ_GRAPH_PATH"):
        return body
    if stripped.startswith("Spatial parser is not available"):
        return body
    if stripped.startswith("Page not found"):
        return body
    if stripped.startswith("Could not read the page file"):
        return body

    lower = stripped.lower()
    if any(
        needle in lower
        for needle in (
            "password::",
            "token::",
            "secret::",
            "api-key::",
            "production",
            "must never",
            "never run",
            "ssh ",
        )
    ):
        hint = RoutingHint.L1_CANDIDATE
    else:
        hint = RoutingHint.L2_DEFAULT
    return stripped + f"\n\n{format_routing_comment(hint)}\n"


def routing_hint_for_write_outline() -> str:
    """Writes through Logseq API append blocks under an existing UUID (L2)."""
    return format_routing_comment(RoutingHint.L2_GRAPH_APPEND)


def routing_hint_for_entity_alias_preflight() -> str:
    """Suggest alias index lookup before creating entity pages (duplicate avoidance)."""
    return format_routing_comment(RoutingHint.RESOLVE_ENTITY)


__all__ = [
    "RoutingHint",
    "append_read_page_routing_hint",
    "format_routing_comment",
    "routing_hint_for_entity_alias_preflight",
    "routing_hint_for_write_outline",
]
