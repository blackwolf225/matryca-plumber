"""Tests for Logseq UUID helpers and block-ref pre-flight guard."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from src.graph.logseq_uuid import (
    assert_valid_block_refs_in_markdown,
    find_malformed_block_refs,
    is_logseq_block_uuid,
)
from src.graph.markdown_blocks import atomic_write_bytes


def test_is_logseq_block_uuid_accepts_v4_and_v5() -> None:
    v4 = "f47ac10b-58cc-4372-a567-0e02b2c3d479"
    v5 = str(uuid.uuid5(uuid.NAMESPACE_DNS, "block"))
    assert is_logseq_block_uuid(v4)
    assert is_logseq_block_uuid(v5)


def test_is_logseq_block_uuid_rejects_v1() -> None:
    u1 = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
    assert not is_logseq_block_uuid(u1)


def test_find_malformed_block_refs_short_uuid() -> None:
    bad = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeee"  # 35 hex chars in last group
    assert find_malformed_block_refs(f"- link (({bad}))") == [bad]


def test_assert_valid_block_refs_raises_on_typo() -> None:
    bad = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeee"
    with pytest.raises(ValueError, match="Malformed UUID"):
        assert_valid_block_refs_in_markdown(f"- link (({bad}))")


def test_atomic_write_bytes_rejects_malformed_block_ref(tmp_path: Path) -> None:
    bad = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeee"
    path = tmp_path / "pages" / "x.md"
    path.parent.mkdir(parents=True)
    with pytest.raises(ValueError, match="Malformed UUID"):
        atomic_write_bytes(path, f"- ref (({bad}))\n".encode(), graph_root=tmp_path)
