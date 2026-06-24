"""Tests for src/graph/safety/validators.py."""

from __future__ import annotations

from src.graph.safety.validators import (
    reject_id_line_deletion,
    reject_protected_zones_modification,
    validate_llm_write_diff,
)


def test_reject_id_line_deletion_blocks_removed_uuid() -> None:
    before = "- item\n  id:: abc-def\n"
    after = "- item\n"
    result = reject_id_line_deletion(before, after)
    assert not result.ok
    assert result.reason == "id_line_deleted"


def test_reject_id_line_deletion_allows_preserved_uuid() -> None:
    text = "- item\n  id:: abc-def\n"
    assert reject_id_line_deletion(text, text).ok


def test_reject_protected_zones_modification_blocks_fence_edit() -> None:
    before = "- intro\n```python\nsecret = 1\n```\n"
    after = "- intro\n```python\nsecret = 2\n```\n"
    result = reject_protected_zones_modification(before, after)
    assert not result.ok
    assert result.reason.startswith("protected_line_modified:")


def test_reject_protected_zones_allows_outside_fence_edit() -> None:
    before = "- intro\n```python\nsecret = 1\n```\n- tail\n"
    after = "- intro edited\n```python\nsecret = 1\n```\n- tail\n"
    assert reject_protected_zones_modification(before, after).ok


def test_validate_llm_write_diff_composes_validators() -> None:
    before = "- item\n  id:: abc-def\n"
    after = "- item\n"
    result = validate_llm_write_diff(before, after)
    assert not result.ok
