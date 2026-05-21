"""Tests for lenient LLM JSON repair utilities."""

from __future__ import annotations

import json

import pytest
from src.agent.plumber_llm import GraphInsightsLLMResult
from src.utils.json_repair import (
    extract_json_object,
    fix_double_escaped_quote_runs,
    loads_repaired_json,
    parse_llm_json,
    repair_llm_json,
    strip_trailing_json_garbage,
)


def test_fix_double_escaped_quote_runs() -> None:
    raw = (
        '{"ontology_report": "The graph remains largely unmapped.\\"\\", '
        '\\"structural_debt\\": \\"high\\"", '
        '"cleanup_suggestions": ["Link orphans"]}'
    )
    repaired = repair_llm_json(raw)
    payload = json.loads(repaired)
    assert "structural_debt" in payload["ontology_report"]
    assert payload["cleanup_suggestions"] == ["Link orphans"]


def test_strip_trailing_garbage_block() -> None:
    raw = '{"ontology_report": "Done.", "cleanup_suggestions": ["Split dense page"]} { "'
    repaired = repair_llm_json(raw)
    payload = json.loads(repaired)
    assert payload["ontology_report"] == "Done."
    assert payload["cleanup_suggestions"] == ["Split dense page"]


def test_extract_json_object_from_markdown_fence() -> None:
    raw = """```json
{"ontology_report": "ok", "cleanup_suggestions": []}
```"""
    extracted = extract_json_object(raw)
    assert json.loads(extracted) == {
        "ontology_report": "ok",
        "cleanup_suggestions": [],
    }


def test_balance_truncated_closing_brackets() -> None:
    raw = '{"ontology_report": "truncated", "cleanup_suggestions": ["a", "b"'
    repaired = repair_llm_json(raw)
    payload = json.loads(repaired)
    assert payload["cleanup_suggestions"] == ["a", "b"]


def test_parse_llm_json_validates_graph_insights_model() -> None:
    raw = (
        '{"ontology_report": "940 pages mapped.", '
        '"cleanup_suggestions": ["Review orphan cluster"]} { "reason": null }'
    )
    result = parse_llm_json(raw, GraphInsightsLLMResult)
    assert result.ontology_report == "940 pages mapped."
    assert result.cleanup_suggestions == ["Review orphan cluster"]


def test_loads_repaired_json_raises_on_unrecoverable_payload() -> None:
    with pytest.raises(json.JSONDecodeError):
        loads_repaired_json("not json at all")


def test_strip_trailing_json_garbage_preserves_valid_suffix() -> None:
    text = '{"a": 1}'
    assert strip_trailing_json_garbage(text) == '{"a": 1}'


def test_fix_double_escaped_quote_runs_helper() -> None:
    assert fix_double_escaped_quote_runs('foo\\"", \\"bar') == 'foo\\", \\"bar'
