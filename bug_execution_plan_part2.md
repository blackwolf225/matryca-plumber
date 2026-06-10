# Bug Execution Plan — Part 2 — Contract for Composer 2.5

> Planner: The Architect. Executioner: Composer 2.5.
> Round 2 scope: 4 NEW high-impact latent bugs in `src/utils/`, `src/semantic/`, and `src/cli/`.
> **Conflict-avoidance guarantee:** this plan does NOT touch any file already queued in `bug_execution_plan.md`. The four reserved files (`src/graph/alias_index.py`, `src/utils/json_repair.py`, `src/agent/journey_log.py`, `src/graph/link_verification.py`) are NOT referenced here.
> Hard constraint: every change is surgical and backward compatible. The suite is at **691 green tests** and MUST stay green (this plan adds 4 new tests).
> Composer: apply the phases **in order**. After each phase run its Verification Command. Run the global gate (bottom of file) only after all 4 phases are applied.

---

## Audit summary

| Phase | File | Bug class | Risk |
|---|---|---|---|
| 1 | `src/utils/bounded_json.py` | TOCTOU: size checked via `stat()`, then full file read separately | Memory-DoS guard bypass |
| 2 | `src/semantic/store.py` | No self-heal: corrupt vector JSON raises uncaught `ValueError`/`TypeError` | Semantic search hard-crash |
| 3 | `src/semantic/indexer.py` | Parsing edge-case: identical `content`/`clean_text` embedded twice | Skewed embeddings / cosine scores |
| 4 | `src/cli/__init__.py` | `plumber stop` always returns exit code 0, even on failure | Broken automation/scripts |

---

### Phase 1: Bounded JSON read has a size-cap TOCTOU bypass

- **Target File:** `src/utils/bounded_json.py`
- **Target Function/Class:** `read_bounded_json`
- **Problem:** The function reads `file_path.stat().st_size`, checks it against `cap`, and only afterwards calls `file_path.read_text()`. Between the `stat()` and the read another process can grow/replace the file, so `read_text()` can load far more than `cap` bytes, defeating the memory-DoS guard. The fix performs a single bounded read of at most `cap + 1` bytes and rejects when the read overflows, closing the race and bounding memory.
- **Required Action for Composer:**
  1. Replace the entire `read_bounded_json` function (currently lines 28-52, from `def read_bounded_json(` down to and including the final `raise BoundedJsonError(f"Invalid JSON in checkpoint: {file_path}") from exc`) with the Exact Code below. Do not change any other function, import, or `__all__`.
  2. Append the regression test (second snippet) to the end of `tests/test_bounded_json.py` (`json`, `pytest`, `Path`, `read_bounded_json`, `BoundedJsonError` are already imported there).
- **Exact Code (Snippet):**

```python
def read_bounded_json(
    path: Path | str,
    *,
    max_bytes: int | None = None,
    encoding: str = "utf-8",
) -> Any:
    """Read and parse JSON from ``path`` after enforcing a byte-size cap."""
    cap = max_bytes if max_bytes is not None else json_max_bytes()
    file_path = Path(path)
    try:
        with file_path.open("rb") as handle:
            data = handle.read(cap + 1)
    except OSError as exc:
        raise BoundedJsonError(f"Cannot read JSON checkpoint: {file_path}") from exc
    if len(data) > cap:
        raise BoundedJsonError(
            f"JSON checkpoint exceeds {cap} bytes: {file_path}",
        )
    try:
        text = data.decode(encoding)
    except UnicodeDecodeError as exc:
        raise BoundedJsonError(f"Cannot decode JSON checkpoint: {file_path}") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise BoundedJsonError(f"Invalid JSON in checkpoint: {file_path}") from exc
```

Regression test to append to `tests/test_bounded_json.py`:

```python
def test_read_bounded_json_caps_via_explicit_max_bytes(tmp_path: Path) -> None:
    path = tmp_path / "big.json"
    path.write_text(json.dumps(list(range(100))), encoding="utf-8")
    with pytest.raises(BoundedJsonError, match="exceeds"):
        read_bounded_json(path, max_bytes=16)
```

- **Verification Command:** `uv run pytest tests/test_bounded_json.py -q`

---

### Phase 2: Block vector store does not self-heal corrupt JSON

- **Target File:** `src/semantic/store.py`
- **Target Function/Class:** `load_block_vector_store`
- **Problem:** Loading wraps `BlockVectorStore.from_json(...)` in `except (BoundedJsonError, OSError)`. A corrupt on-disk record such as `"vec_content": null` makes `BlockVectorRecord.from_json` do `[float(x) for x in None]`, raising `TypeError`; `"vec_content": ["1.0", "bad"]` raises `ValueError`. Neither is caught, so `load_block_vector_store` (and every `hybrid_block_search` caller) hard-crashes instead of self-healing to an empty store the way `master_catalog` does. The fix widens the `except` to also catch `ValueError` and `TypeError`, leaving the already-constructed fresh empty `store` as the fallback.
- **Required Action for Composer:** In `load_block_vector_store`, replace the single `except` clause (currently lines 221-222) with the Exact Code below. Keep the surrounding `try` / `with cross_process_json_flock(path):` / `store = BlockVectorStore.from_json(...)` body exactly as-is.
- **Exact Code (Snippet):**

```python
            except (BoundedJsonError, OSError, ValueError, TypeError) as exc:
                logger.warning("Failed to load block_vectors.json: {}", exc)
```

Regression test to append to `tests/test_dual_embedding.py` (`load_block_vector_store` and `clear_block_vector_store_cache` are already imported there):

```python
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
```

- **Verification Command:** `uv run pytest tests/test_dual_embedding.py -q`

---

### Phase 3: Embedding text duplicates identical content and clean_text

- **Target File:** `src/semantic/indexer.py`
- **Target Function/Class:** `_block_text`
- **Problem:** `_block_text` joins `node.content` and `node.clean_text` unconditionally. For a plain block the parser sets both fields to the same string, so the embedded text becomes `"Deploy checklist Deploy checklist"`, skewing `vec_content`, applicability synthesis, and hybrid cosine scoring. The fix de-duplicates exact repeats while preserving order, so distinct `content` vs `clean_text` (markup vs cleaned) are still both included.
- **Required Action for Composer:**
  1. Replace the entire `_block_text` function (currently lines 26-28) with the Exact Code below.
  2. Append the regression test (second snippet) to the end of `tests/test_dual_embedding.py`.
- **Exact Code (Snippet):**

```python
def _block_text(node: LogseqNode) -> str:
    parts: list[str] = []
    for raw in (node.content or "", node.clean_text or ""):
        text = raw.strip()
        if text and text not in parts:
            parts.append(text)
    return " ".join(parts).strip()
```

Regression test to append to `tests/test_dual_embedding.py`:

```python
def test_block_text_dedupes_identical_content_and_clean_text() -> None:
    from types import SimpleNamespace
    from typing import Any

    from src.semantic.indexer import _block_text

    node: Any = SimpleNamespace(content="Deploy checklist", clean_text="Deploy checklist")
    assert _block_text(node) == "Deploy checklist"
```

- **Verification Command:** `uv run pytest tests/test_dual_embedding.py -q`

---

### Phase 4: `plumber stop` always exits 0, even on failure

- **Target File:** `src/cli/__init__.py`
- **Target Function/Class:** `run_cli` (the `plumber_action == "stop"` branch)
- **Problem:** Unlike the sibling `start`, `audit`, and `cluster` branches (which return `0 if out.get("ok") is not False else 1`), the `stop` branch hardcodes `return 0`. When `stop_daemon` returns `{"ok": False, ...}` (no PID, foreign PID, signal failed), the CLI still exits 0, so automation believes the daemon stopped. The fix mirrors the sibling branches.
- **Required Action for Composer:** In `run_cli`, replace the `stop` branch (currently lines 349-352) with the Exact Code below. Only the final `return` line changes; keep the `if`, `stop_out = stop_daemon(graph_root)`, and `_emit_result(...)` lines identical.
- **Exact Code (Snippet):**

```python
        if plumber_action == "stop":
            stop_out = stop_daemon(graph_root)
            _emit_result(stop_out, as_json=as_json, command=command)
            return 0 if stop_out.get("ok") is not False else 1
```

Regression test to append to `tests/test_cli.py` (`Namespace`, `Path`, `pytest`, and `run_cli` are already imported there):

```python
@pytest.mark.asyncio
async def test_plumber_stop_returns_nonzero_when_not_ok(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.cli as cli

    monkeypatch.setattr(cli, "resolve_graph_root", lambda: Path("/tmp"))
    monkeypatch.setattr(cli, "stop_daemon", lambda _root: {"ok": False, "reason": "no daemon"})
    args = Namespace(command="plumber", plumber_action="stop", json=True)
    code = await run_cli(args)
    assert code == 1
```

- **Verification Command:** `uv run pytest tests/test_cli.py -q`

---

## Global verification gate (run once, after all 4 phases)

```bash
uv run ruff check src tests
uv run mypy src tests
uv run pytest -q
```

Success criteria: ruff clean, mypy clean, **all tests green (>= 691 baseline + 4 new = 695)**. If any phase fails verification, fix only the code introduced by that phase and re-run — do not touch unrelated code, and never edit any of the four files reserved by `bug_execution_plan.md`.
