"""Tests for L1/L2 routing hint footer."""

from __future__ import annotations

from src.agent.routing_hint import (
    RoutingHint,
    append_read_page_routing_hint,
    format_routing_comment,
    routing_hint_for_entity_alias_preflight,
    routing_hint_for_write_outline,
)


def test_routing_hint_enum_values_stable() -> None:
    assert RoutingHint.L1_CANDIDATE.value == "L1_candidate"
    assert RoutingHint.L2_DEFAULT.value == "L2_default"
    assert RoutingHint.L2_GRAPH_APPEND.value == "L2_graph_append"
    assert RoutingHint.RESOLVE_ENTITY.value == "call_search_graph_resolve_entity_for_entities"


def test_format_routing_comment() -> None:
    assert format_routing_comment(RoutingHint.L2_GRAPH_APPEND) == (
        "<!-- matryca_routing: hint=L2_graph_append -->"
    )


def test_write_outline_and_entity_preflight_helpers() -> None:
    assert routing_hint_for_write_outline() == format_routing_comment(
        RoutingHint.L2_GRAPH_APPEND,
    )
    assert routing_hint_for_entity_alias_preflight() == format_routing_comment(
        RoutingHint.RESOLVE_ENTITY,
    )


def test_routing_hint_skips_error_messages() -> None:
    body = "LOGSEQ_GRAPH_PATH is not set in the environment"
    assert append_read_page_routing_hint(body) == body


def test_routing_hint_appends_for_normal_page() -> None:
    body = "# Spatial view\n\nSome content about deployment."
    out = append_read_page_routing_hint(body)
    assert format_routing_comment(RoutingHint.L2_DEFAULT) in out


def test_routing_hint_sensitive_content_uses_l1() -> None:
    body = "password:: do not commit"
    out = append_read_page_routing_hint(body)
    assert format_routing_comment(RoutingHint.L1_CANDIDATE) in out
