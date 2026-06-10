"""Tests for dual embedding storage and hybrid retrieval."""

from __future__ import annotations

from pathlib import Path

import pytest
from src.semantic.applicability import synthesize_applicability
from src.semantic.config import hybrid_weights
from src.semantic.indexer import index_page_blocks
from src.semantic.math_util import cosine_similarity, hybrid_score
from src.semantic.search import hybrid_block_search
from src.semantic.store import (
    BlockVectorRecord,
    clear_block_vector_store_cache,
    load_block_vector_store,
)


class MockApplicabilityLLM:
    def complete_applicability(self, block_text: str) -> str:
        return f"Useful when asking about: {block_text[:40]}"


class MockEmbeddingClient:
    """Deterministic vectors keyed by exact input text."""

    _TABLE: dict[str, list[float]] = {
        "query": [1.0, 0.0],
        "alpha content": [1.0, 0.0],
        "beta content": [0.0, 1.0],
        "Useful when asking about: alpha content": [0.8, 0.2],
        "Useful when asking about: beta content": [0.2, 0.8],
    }

    def embed_text(self, text: str) -> list[float]:
        key = text.strip()
        if key in self._TABLE:
            return list(self._TABLE[key])
        return [0.1, 0.1]


def test_cosine_similarity_identical() -> None:
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)


def test_hybrid_score_respects_weights(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MATRYCA_WEIGHT_CONTENT", "0.7")
    monkeypatch.setenv("MATRYCA_WEIGHT_APPLICABILITY", "0.3")
    weights = hybrid_weights()
    query = [1.0, 0.0]
    content_match = [1.0, 0.0]
    app_orthogonal = [0.0, 1.0]
    score = hybrid_score(
        query,
        content_match,
        app_orthogonal,
        weight_content=weights.content,
        weight_applicability=weights.applicability,
    )
    assert score == pytest.approx(0.7)


def test_synthesize_applicability_mock() -> None:
    out = synthesize_applicability("alpha content", MockApplicabilityLLM())
    assert "alpha" in out


def test_block_vector_store_round_trip(tmp_path: Path) -> None:
    clear_block_vector_store_cache()
    store = load_block_vector_store(tmp_path)
    store.upsert(
        "uuid-a",
        BlockVectorRecord(
            page_title="Demo",
            block_text="hello",
            applicability_text="when greeting",
            vec_content=[1.0, 0.0],
            vec_applicability=[0.5, 0.5],
            updated_at="2026-01-01T00:00:00+00:00",
        ),
    )
    store.save()
    reloaded = load_block_vector_store(tmp_path, force_reload=True)
    record = reloaded.blocks["uuid-a"]
    assert record.page_title == "Demo"
    assert record.vec_content == [1.0, 0.0]


def test_hybrid_block_search_ranking(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_block_vector_store_cache()
    monkeypatch.setenv("MATRYCA_DUAL_EMBEDDING_ENABLED", "true")
    monkeypatch.setenv("MATRYCA_WEIGHT_CONTENT", "0.5")
    monkeypatch.setenv("MATRYCA_WEIGHT_APPLICABILITY", "0.5")

    store = load_block_vector_store(tmp_path)
    store.upsert(
        "uuid-alpha",
        BlockVectorRecord(
            page_title="P",
            block_text="alpha content",
            applicability_text="Useful when asking about: alpha content",
            vec_content=[1.0, 0.0],
            vec_applicability=[0.8, 0.2],
            updated_at="t",
        ),
    )
    store.upsert(
        "uuid-beta",
        BlockVectorRecord(
            page_title="P",
            block_text="beta content",
            applicability_text="Useful when asking about: beta content",
            vec_content=[0.0, 1.0],
            vec_applicability=[0.2, 0.8],
            updated_at="t",
        ),
    )
    store.save()

    client = MockEmbeddingClient()
    hits = hybrid_block_search(tmp_path, "query", embedding_client=client, limit=5)
    assert hits
    assert hits[0].block_uuid == "uuid-alpha"
    assert hits[0].final_score >= hits[1].final_score


def test_index_page_blocks_noop_when_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MATRYCA_DUAL_EMBEDDING_ENABLED", raising=False)
    pages = tmp_path / "pages"
    pages.mkdir(parents=True)
    block_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    (pages / "Demo.md").write_text(
        f"- Alpha bullet\n  id:: {block_id}\n",
        encoding="utf-8",
    )
    count = index_page_blocks(
        tmp_path,
        pages / "Demo.md",
        "Demo",
        llm_client=MockApplicabilityLLM(),
        embedding_client=MockEmbeddingClient(),
    )
    assert count == 0


def test_index_page_blocks_when_enabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage

    monkeypatch.setenv("MATRYCA_DUAL_EMBEDDING_ENABLED", "true")
    block_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    node = LogseqNode.model_validate(
        {
            "uuid": block_id,
            "source_uuid": block_id,
            "content": "Alpha bullet",
            "clean_text": "Alpha bullet",
            "indent_level": 0,
            "properties": {"id": block_id},
            "children": [],
            "synthetic_id": False,
        },
    )
    page = LogseqPage.model_validate(
        {
            "title": "Demo",
            "raw_content": "- Alpha bullet",
            "root_nodes": [node],
        },
    )

    class _FakeGraph:
        pages = {"Demo": page}

    class _FakeCache:
        def apply_file_event(self, path: Path, kind: str) -> None:
            _ = path, kind

        def get_graph(self) -> _FakeGraph:
            return _FakeGraph()

    monkeypatch.setattr(
        "src.semantic.indexer.get_graph_ast_cache",
        lambda _root: _FakeCache(),
    )
    clear_block_vector_store_cache()
    page_path = tmp_path / "pages" / "Demo.md"
    page_path.parent.mkdir(parents=True)
    page_path.write_text(f"- Alpha bullet\n  id:: {block_id}\n", encoding="utf-8")

    count = index_page_blocks(
        tmp_path,
        page_path,
        "Demo",
        llm_client=MockApplicabilityLLM(),
        embedding_client=MockEmbeddingClient(),
    )
    assert count == 1
    store = load_block_vector_store(tmp_path, force_reload=True)
    assert block_id in store.blocks


def test_index_page_blocks_preserves_vectors_when_embed_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from logseq_matryca_parser.logos_core import LogseqNode, LogseqPage

    block_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    node = LogseqNode.model_validate(
        {
            "uuid": block_id,
            "source_uuid": block_id,
            "content": "Alpha bullet",
            "clean_text": "Alpha bullet",
            "indent_level": 0,
            "properties": {"id": block_id},
            "children": [],
            "synthetic_id": False,
        },
    )
    page = LogseqPage.model_validate(
        {
            "title": "Demo",
            "raw_content": "- Alpha bullet",
            "root_nodes": [node],
        },
    )

    class _FakeGraph:
        pages = {"Demo": page}

    class _FakeCache:
        def apply_file_event(self, path: Path, kind: str) -> None:
            _ = path, kind

        def get_graph(self) -> _FakeGraph:
            return _FakeGraph()

    class _FailingApplicability:
        def complete_applicability(self, block_text: str) -> str:
            raise RuntimeError("embed down")

    monkeypatch.setattr(
        "src.semantic.indexer.get_graph_ast_cache",
        lambda _root: _FakeCache(),
    )
    monkeypatch.setenv("MATRYCA_DUAL_EMBEDDING_ENABLED", "true")
    clear_block_vector_store_cache()
    store = load_block_vector_store(tmp_path)
    store.upsert(
        block_id,
        BlockVectorRecord(
            page_title="Demo",
            block_text="old",
            applicability_text="old",
            vec_content=[1.0, 0.0],
            vec_applicability=[1.0, 0.0],
            updated_at="t",
        ),
    )
    store.save()
    clear_block_vector_store_cache()

    page_path = tmp_path / "pages" / "Demo.md"
    page_path.parent.mkdir(parents=True)
    page_path.write_text(f"- Alpha bullet\n  id:: {block_id}\n", encoding="utf-8")

    count = index_page_blocks(
        tmp_path,
        page_path,
        "Demo",
        llm_client=_FailingApplicability(),
        embedding_client=MockEmbeddingClient(),
    )
    assert count == 0
    reloaded = load_block_vector_store(tmp_path, force_reload=True)
    assert block_id in reloaded.blocks


def test_index_page_blocks_keeps_vectors_when_page_missing_from_ast(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MATRYCA_DUAL_EMBEDDING_ENABLED", "true")

    class _EmptyGraph:
        pages: dict[str, object] = {}

    class _FakeCache:
        def apply_file_event(self, path: Path, kind: str) -> None:
            _ = path, kind

        def get_graph(self) -> _EmptyGraph:
            return _EmptyGraph()

    monkeypatch.setattr(
        "src.semantic.indexer.get_graph_ast_cache",
        lambda _root: _FakeCache(),
    )
    clear_block_vector_store_cache()
    store = load_block_vector_store(tmp_path)
    store.upsert(
        "keep-me",
        BlockVectorRecord(
            page_title="Demo",
            block_text="stale",
            applicability_text="stale",
            vec_content=[1.0, 0.0],
            vec_applicability=[1.0, 0.0],
            updated_at="t",
        ),
    )
    store.save()
    clear_block_vector_store_cache()

    page_path = tmp_path / "pages" / "Demo.md"
    page_path.parent.mkdir(parents=True)
    page_path.write_text("- x\n", encoding="utf-8")

    count = index_page_blocks(
        tmp_path,
        page_path,
        "Demo",
        llm_client=MockApplicabilityLLM(),
        embedding_client=MockEmbeddingClient(),
    )
    assert count == 0
    reloaded = load_block_vector_store(tmp_path, force_reload=True)
    assert "keep-me" in reloaded.blocks


def test_index_page_blocks_prunes_when_no_indexable_nodes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from logseq_matryca_parser.logos_core import LogseqPage

    monkeypatch.setenv("MATRYCA_DUAL_EMBEDDING_ENABLED", "true")
    page = LogseqPage.model_validate(
        {
            "title": "Demo",
            "raw_content": "- plain bullet without id",
            "root_nodes": [],
        },
    )

    class _FakeGraph:
        pages = {"Demo": page}

    class _FakeCache:
        def apply_file_event(self, path: Path, kind: str) -> None:
            _ = path, kind

        def get_graph(self) -> _FakeGraph:
            return _FakeGraph()

    monkeypatch.setattr(
        "src.semantic.indexer.get_graph_ast_cache",
        lambda _root: _FakeCache(),
    )
    clear_block_vector_store_cache()
    store = load_block_vector_store(tmp_path)
    store.upsert(
        "orphan-uuid",
        BlockVectorRecord(
            page_title="Demo",
            block_text="stale",
            applicability_text="stale",
            vec_content=[1.0, 0.0],
            vec_applicability=[1.0, 0.0],
            updated_at="t",
        ),
    )
    store.save()
    clear_block_vector_store_cache()

    page_path = tmp_path / "pages" / "Demo.md"
    page_path.parent.mkdir(parents=True)
    page_path.write_text("- plain bullet without id\n", encoding="utf-8")

    count = index_page_blocks(
        tmp_path,
        page_path,
        "Demo",
        llm_client=MockApplicabilityLLM(),
        embedding_client=MockEmbeddingClient(),
    )
    assert count == 0
    reloaded = load_block_vector_store(tmp_path, force_reload=True)
    assert "orphan-uuid" not in reloaded.blocks


def test_block_vector_store_reload_when_disk_mtime_changes(tmp_path: Path) -> None:
    clear_block_vector_store_cache()
    store = load_block_vector_store(tmp_path)
    store.upsert(
        "uuid-a",
        BlockVectorRecord(
            page_title="P",
            block_text="alpha",
            applicability_text="when alpha",
            vec_content=[1.0, 0.0],
            vec_applicability=[0.8, 0.2],
            updated_at="t",
        ),
    )
    store.save()
    first = load_block_vector_store(tmp_path)
    assert "uuid-a" in first.blocks

    path = first.store_path(tmp_path)
    import json
    import time

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["blocks"]["uuid-b"] = {
        "page_title": "P",
        "block_text": "beta",
        "applicability_text": "when beta",
        "vec_content": [0.0, 1.0],
        "vec_applicability": [0.2, 0.8],
        "updated_at": "t2",
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    time.sleep(0.02)

    second = load_block_vector_store(tmp_path)
    assert "uuid-b" in second.blocks


def test_index_page_blocks_skips_without_flag_enabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MATRYCA_DUAL_EMBEDDING_ENABLED", "false")
    pages = tmp_path / "pages"
    pages.mkdir(parents=True)
    (pages / "Demo.md").write_text("- No id line\n", encoding="utf-8")
    count = index_page_blocks(
        tmp_path,
        pages / "Demo.md",
        "Demo",
        llm_client=MockApplicabilityLLM(),
        embedding_client=MockEmbeddingClient(),
    )
    assert count == 0


def test_load_block_vector_store_self_heals_corrupt_vectors(tmp_path: Path) -> None:
    import json

    clear_block_vector_store_cache()
    cache_dir = tmp_path / ".matryca_semantic_cache"
    cache_dir.mkdir(parents=True)
    (cache_dir / "block_vectors.json").write_text(
        json.dumps(
            {
                "version": 1,
                "blocks": {
                    "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee": {
                        "page_title": "P",
                        "block_text": "x",
                        "applicability_text": "",
                        "vec_content": None,
                        "vec_applicability": [],
                        "updated_at": "",
                    },
                },
            },
        ),
        encoding="utf-8",
    )
    store = load_block_vector_store(tmp_path, force_reload=True)
    assert store.blocks == {}


def test_block_text_dedupes_identical_content_and_clean_text() -> None:
    from types import SimpleNamespace
    from typing import Any

    from src.semantic.indexer import _block_text

    node: Any = SimpleNamespace(content="Deploy checklist", clean_text="Deploy checklist")
    assert _block_text(node) == "Deploy checklist"
