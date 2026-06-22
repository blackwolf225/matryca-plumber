"""Tests for shadow.sqlite DDL scaffold."""

from __future__ import annotations

import sqlite3

from src.shadow.schema import (
    SHADOW_SCHEMA_VERSION,
    apply_shadow_schema,
)


def test_apply_shadow_schema_in_memory() -> None:
    conn = sqlite3.connect(":memory:")
    try:
        apply_shadow_schema(conn)
        version = conn.execute(
            "SELECT value FROM shadow_meta WHERE key = 'schema_version'",
        ).fetchone()
        assert version is not None
        assert version[0] == str(SHADOW_SCHEMA_VERSION)

        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'",
            )
        }
        for name in (
            "shadow_meta",
            "pages",
            "blocks",
            "block_refs",
            "memory_nodes",
            "memory_edges",
            "memory_pending_edges",
            "memory_episodes",
            "memory_episode_entities",
            "memory_procedures",
            "memory_snapshots",
        ):
            assert name in tables

        fts = conn.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'blocks_fts'",
        ).fetchone()
        assert fts is not None
        assert "fts5" in fts[0].lower()
    finally:
        conn.close()


def test_blocks_fts_trigger_on_insert() -> None:
    conn = sqlite3.connect(":memory:")
    try:
        apply_shadow_schema(conn)
        conn.execute(
            "INSERT INTO pages (title, file_path, file_mtime_ns, file_size, synced_at) "
            "VALUES ('Test', 'pages/Test.md', 1, 10, '2026-01-01T00:00:00Z')",
        )
        page_id = conn.execute("SELECT page_id FROM pages").fetchone()[0]
        conn.execute(
            "INSERT INTO blocks (block_uuid, page_id, sort_order, content, synced_at) "
            "VALUES ('uuid-1', ?, 0, 'hello shadow fts', '2026-01-01T00:00:00Z')",
            (page_id,),
        )
        hit = conn.execute(
            "SELECT block_uuid FROM blocks WHERE rowid IN ("
            "SELECT rowid FROM blocks_fts WHERE blocks_fts MATCH 'shadow'"
            ")",
        ).fetchone()
        assert hit is not None
        assert hit[0] == "uuid-1"
    finally:
        conn.close()
