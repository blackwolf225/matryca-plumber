# Bug Execution Plan — Part 3 — Contract for Composer 2.5

> Planner: The Architect. Executioner: Composer 2.5.
> Round 3 scope: 4 NEW high-impact latent bugs in `src/agent/graph_tool_helpers.py`, `src/utils/runtime_bootstrap.py`, and `src/agent/plumber_modules/semantic_cache_router.py`.
> **Conflict-avoidance guarantee:** this plan does NOT touch any file already queued in `bug_execution_plan.md` or `bug_execution_plan_part2.md`. The eight reserved files are NOT referenced as targets here.
> Hard constraint: every change is surgical and backward compatible. The suite is at **691 green tests** and MUST stay green (this plan adds 5 new tests → ~696 green).
> Composer: apply the phases **in order**. After each phase run its Verification Command. Run the global gate (bottom of file) only after all 4 phases are applied. Match the exact `old` code shown; do not rely on line numbers alone (Phases 1 and 2 edit the same file).

---

## Audit summary

| Phase | File | Bug class | Risk |
|---|---|---|---|
| 1 | `src/agent/graph_tool_helpers.py` | Type-coercion: JSON booleans silently pass `int()` | Wrong/clamped tool args |
| 2 | `src/agent/graph_tool_helpers.py` | Parsing edge-case: heading filter leaks sibling sections | LLM gets wrong subtree |
| 3 | `src/utils/runtime_bootstrap.py` | Path traversal: `templates_subdir` not validated | Dirs created outside the vault |
| 4 | `src/agent/plumber_modules/semantic_cache_router.py` | Cache key collision: basename-only key | Wrong cached inference returned |

---

### Phase 1: `bounded_int_from_options` silently coerces JSON booleans

- **Target File:** `src/agent/graph_tool_helpers.py`
- **Target Function/Class:** `bounded_int_from_options`
- **Problem:** In Python `int(False) == 0` and `int(True) == 1`, so a JSON option like `{"limit": false}` (not `None`) is coerced and clamped to `minimum` instead of being rejected, silently corrupting `limit` / `days` / `max_depth` passed from `graph_dispatch.py`. The fix rejects `bool` before `int()`.
- **Required Action for Composer:**
  1. In `bounded_int_from_options`, replace the exact `old` block below (the `raw = opts[key]` line through the `except` return) with the `new` block. Insert the `isinstance(raw, bool)` guard immediately after `raw = opts[key]`.
  2. Append the two regression tests (second snippet) to the end of `tests/test_graph_tool_helpers_bounded_int.py` (`bounded_int_from_options` is already imported there).
- **Exact Code (Snippet):**

Replace this exact block:

```python
    raw = opts[key]
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return f"Invalid integer for `{key}`: {raw!r}"
```

with:

```python
    raw = opts[key]
    if isinstance(raw, bool):
        return f"Invalid integer for `{key}`: {raw!r}"
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return f"Invalid integer for `{key}`: {raw!r}"
```

Regression tests to append to `tests/test_graph_tool_helpers_bounded_int.py`:

```python
def test_bounded_int_from_options_rejects_bool_false() -> None:
    result = bounded_int_from_options(
        {"limit": False},
        "limit",
        default=15,
        minimum=1,
        maximum=100,
    )
    assert isinstance(result, str)
    assert "Invalid integer" in result


def test_bounded_int_from_options_rejects_bool_true() -> None:
    result = bounded_int_from_options(
        {"limit": True},
        "limit",
        default=15,
        minimum=1,
        maximum=100,
    )
    assert isinstance(result, str)
    assert "Invalid integer" in result
```

- **Verification Command:** `uv run pytest tests/test_graph_tool_helpers_bounded_int.py -q`

---

### Phase 2: Subtree heading filter leaks sibling sections

- **Target File:** `src/agent/graph_tool_helpers.py`
- **Target Function/Class:** `read_subtree_markdown` (the `if heading_filter:` block)
- **Problem:** After a heading match, inclusion is gated on the subtree-root indent (`root_indent`) instead of the matched heading's indent, so any later sibling bullet deeper than the root (but at/above the heading indent) is wrongly appended — the LLM receives the wrong section. The fix tracks the matched heading's own indent and stops at the next bullet at or above that indent.
- **Required Action for Composer:** In `read_subtree_markdown`, replace the entire `if heading_filter:` block (exact `old` below) with the `new` block. This swaps `root_indent` for `heading_indent` (captured at the moment of the heading match) and only matches the heading while not yet `include`d.
- **Exact Code (Snippet):**

Replace this exact block:

```python
    if heading_filter:
        heading_needle = heading_filter.lstrip("#").strip().lower()
        filtered: list[str] = []
        include = False
        bullet_match = re.compile(r"^(\s*)-\s+(.*)$")
        root_indent: int | None = None
        for line in excerpt_lines:
            stripped_line = line.rstrip("\n")
            match = bullet_match.match(stripped_line)
            if match:
                indent = len(match.group(1))
                text_part = match.group(2).strip()
                if root_indent is None:
                    root_indent = indent
                if text_part.lstrip("#").strip().lower() == heading_needle:
                    include = True
                    filtered = [line]
                    continue
                if include and indent > (root_indent or 0):
                    filtered.append(line)
                elif include and indent <= (root_indent or 0):
                    break
            elif include:
                filtered.append(line)
        excerpt_lines = filtered or excerpt_lines
```

with:

```python
    if heading_filter:
        heading_needle = heading_filter.lstrip("#").strip().lower()
        filtered: list[str] = []
        include = False
        bullet_match = re.compile(r"^(\s*)-\s+(.*)$")
        heading_indent: int | None = None
        for line in excerpt_lines:
            stripped_line = line.rstrip("\n")
            match = bullet_match.match(stripped_line)
            if match:
                indent = len(match.group(1))
                text_part = match.group(2).strip()
                if not include:
                    if text_part.lstrip("#").strip().lower() == heading_needle:
                        include = True
                        heading_indent = indent
                        filtered = [line]
                    continue
                if heading_indent is not None and indent > heading_indent:
                    filtered.append(line)
                else:
                    break
            elif include:
                filtered.append(line)
        excerpt_lines = filtered or excerpt_lines
```

Regression test to append to `tests/test_graph_tool_helpers_bounded_int.py`. Also add `import json` and `from pathlib import Path` to that file's import block (after the existing `from __future__ import annotations` line):

```python
def test_read_subtree_heading_excludes_sibling_sections(tmp_path: Path) -> None:
    from src.agent.graph_tool_helpers import read_subtree_markdown

    block_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    pages = tmp_path / "pages"
    pages.mkdir(parents=True)
    (pages / "Demo.md").write_text(
        f"- Root\n  id:: {block_id}\n"
        "  - Section B\n    - b1\n"
        "  - Section C\n    - c1\n",
        encoding="utf-8",
    )
    query = json.dumps({"page": "Demo", "block_uuid": block_id, "heading": "Section B"})
    md = read_subtree_markdown(str(tmp_path), query)
    assert "Section B" in md
    assert "b1" in md
    assert "Section C" not in md
    assert "c1" not in md
```

- **Verification Command:** `uv run pytest tests/test_graph_tool_helpers_bounded_int.py -q`

---

### Phase 3: `templates_subdir` allows directory creation outside the vault

- **Target File:** `src/utils/runtime_bootstrap.py`
- **Target Function/Class:** `ensure_graph_runtime_directories`
- **Problem:** `templates_subdir` (read from `matryca-wiki.yml`) is only `.strip("/\\")`-ed, so a value like `../outside` is joined to the graph root and `mkdir` creates a directory **outside** the vault. The fix splits the value into path segments and rejects any `..` traversal, falling back to `templates`. (`re` and `logger` are already imported in this module.)
- **Required Action for Composer:** Replace the entire `ensure_graph_runtime_directories` function (exact `old` below) with the `new` block.
- **Exact Code (Snippet):**

Replace this exact function:

```python
def ensure_graph_runtime_directories(
    graph_root: Path,
    *,
    templates_subdir: str = "templates",
) -> None:
    """Create graph-local Matryca working directories (cache, templates)."""
    root = graph_root.expanduser().resolve(strict=False)
    (root / _SEMANTIC_CACHE_DIR).mkdir(parents=True, exist_ok=True)
    subdir = (templates_subdir or "templates").strip().strip("/\\")
    if subdir:
        (root / subdir).mkdir(parents=True, exist_ok=True)
```

with:

```python
def ensure_graph_runtime_directories(
    graph_root: Path,
    *,
    templates_subdir: str = "templates",
) -> None:
    """Create graph-local Matryca working directories (cache, templates)."""
    root = graph_root.expanduser().resolve(strict=False)
    (root / _SEMANTIC_CACHE_DIR).mkdir(parents=True, exist_ok=True)
    subdir = (templates_subdir or "templates").strip().strip("/\\")
    parts = [segment for segment in re.split(r"[/\\]+", subdir) if segment]
    if any(segment == ".." for segment in parts):
        logger.warning(
            "Ignoring unsafe templates_subdir {!r} (path traversal); using 'templates'",
            templates_subdir,
        )
        parts = ["templates"]
    if parts:
        root.joinpath(*parts).mkdir(parents=True, exist_ok=True)
```

Regression test to append to `tests/test_runtime_bootstrap.py` (`ensure_graph_runtime_directories` and `Path` are already imported there):

```python
def test_ensure_graph_runtime_directories_rejects_traversal(tmp_path: Path) -> None:
    graph = tmp_path / "vault"
    graph.mkdir()
    ensure_graph_runtime_directories(graph, templates_subdir="../evil")
    assert not (tmp_path / "evil").exists()
    assert (graph / "templates").is_dir()
```

- **Verification Command:** `uv run pytest tests/test_runtime_bootstrap.py -q`

---

### Phase 4: Semantic cache key collides on identical basenames

- **Target File:** `src/agent/plumber_modules/semantic_cache_router.py`
- **Target Function/Class:** `semantic_cache_key`
- **Problem:** The key uses only `page_path.name` plus mtime, so two pages with the same basename in different namespace folders (e.g. `pages/ns1/Foo.md` and `pages/ns2/Foo.md`) sharing an mtime collide, returning the wrong cached inference. The fix prefixes the immediate parent directory name to disambiguate. (Key format change causes only a one-time, self-recovering cache miss for pre-existing entries.)
- **Required Action for Composer:** Replace the entire `semantic_cache_key` function (exact `old` below) with the `new` block. Only the `rel = ...` line changes.
- **Exact Code (Snippet):**

Replace this exact function:

```python
def semantic_cache_key(page_path: Path, operation: str) -> str:
    """Build a stable key from page path + mtime + operation name."""
    try:
        mtime_ns = page_path.stat().st_mtime_ns
    except OSError:
        mtime_ns = 0
    rel = page_path.name
    return f"{operation}:{rel}:{mtime_ns}"
```

with:

```python
def semantic_cache_key(page_path: Path, operation: str) -> str:
    """Build a stable key from page path + mtime + operation name."""
    try:
        mtime_ns = page_path.stat().st_mtime_ns
    except OSError:
        mtime_ns = 0
    parent = page_path.parent.name
    rel = f"{parent}/{page_path.name}" if parent else page_path.name
    return f"{operation}:{rel}:{mtime_ns}"
```

Regression test to append to `tests/test_semantic_cache_router.py` (`semantic_cache_key` and `Path` are already imported there):

```python
def test_semantic_cache_key_disambiguates_same_basename(tmp_path: Path) -> None:
    import os

    a = tmp_path / "ns1" / "Foo.md"
    a.parent.mkdir(parents=True)
    a.write_text("- x\n", encoding="utf-8")
    b = tmp_path / "ns2" / "Foo.md"
    b.parent.mkdir(parents=True)
    b.write_text("- x\n", encoding="utf-8")
    os.utime(a, ns=(1_000_000_000, 1_000_000_000))
    os.utime(b, ns=(1_000_000_000, 1_000_000_000))
    assert semantic_cache_key(a, "op") != semantic_cache_key(b, "op")
```

- **Verification Command:** `uv run pytest tests/test_semantic_cache_router.py -q`

---

## Global verification gate (run once, after all 4 phases)

```bash
uv run ruff check src tests
uv run mypy src tests
uv run pytest -q
```

Success criteria: ruff clean, mypy clean, **all tests green (>= 691 baseline + 5 new ≈ 696)**. If any phase fails verification, fix only the code introduced by that phase and re-run — do not touch unrelated code, and never edit any of the eight files reserved by `bug_execution_plan.md` / `bug_execution_plan_part2.md`.
