# Contributing to Matryca Plumber

Thank you for investing your time in **Matryca Plumber** (`matryca-plumber`).

This project exists so AI agents can collaborate on **Logseq OG** graphs the right way: **blocks**, **`id::`**, and **local Markdown** — not flattened blobs in someone else's database. Whether you fix a typo, tighten a test, or add an MCP tool, you are helping keep that bar high.

---

## Philosophy (non-negotiable)

Matryca Plumber is built on three pillars. Every contribution must respect them:

| Pillar | Meaning |
|--------|---------|
| **Local-first** | The Logseq graph on disk (`LOGSEQ_GRAPH_PATH`) is the system of record. Reads and writes go through UTF-8 Markdown I/O, `fcntl.flock` RMW locks, and atomic swaps — not a hosted sync service. |
| **Zero external databases** | No SQLite, Postgres, Redis, or cloud DB as a dependency for core behavior. Ephemeral in-memory indexes and JSON ledgers at the graph root are allowed; the vault itself stays pure Markdown. |
| **Absolute Logseq AST parity** | Spatial structure comes from **`logseq_matryca_parser`** and bounded helpers in `src/graph/`. Mutations must preserve outliner semantics: nested bullets, property planes, multiline continuations, and fence-protected dead zones. |

Deep reference: [`SYSTEM_PROMPT.md`](SYSTEM_PROMPT.md), [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Phase 0–4 Hardening Rules

These rules are enforced in code and in CI. **Violating them in a PR will be rejected**, even if tests pass by accident.

### Phase 0 — Paradigm lock

- Operate only on files inside the designated graph root (`path_sandbox.assert_path_within_graph`).
- Never introduce a central database, ORM, or external state store for graph content.
- Prefer direct file I/O over the Logseq HTTP API for background linting, indexing, and analysis.

### Phase 1 — OCC snapshot (Optimistic Concurrency Control)

Humans and the Plumber daemon edit the **same** `.md` files concurrently. Local LLM inference is slow; a naive read-modify-write would overwrite live edits.

**Rule:** Before reading page content for any mutation path, capture a **Phase-1 snapshot**:

1. Record `st_mtime` via `read_file_mtime()` / `OCCSnapshot.capture()` in `src/graph/markdown_blocks.py`.
2. Hold that `baseline_mtime` for the entire inference or edit assembly window.

**No contributor may write to the filesystem on a mutation path without first establishing this baseline.**

### Phase 2 — OCC verification

**Rule:** Immediately before committing bytes to disk, run **Phase-2 verification**:

1. Call `occ_verify_before_write()` or commit through `atomic_write_bytes_if_unchanged()`.
2. If `file_mtime_drifted()` is true (the user edited in Logseq during inference), **abort the write** — return `False`, log the skip, and preserve the human's changes.
3. Only when mtime still matches, commit via temp file → `fsync` → `os.replace` under `page_rmw_lock`.

OCC complements `fcntl.flock` (no torn writes) with **lost-update prevention** (no silent overwrites).

### Phase 3 — AST parity

Logseq OG's on-disk contract is strict. Violations cause silent index corruption.

| Topic | Rule |
|-------|------|
| **Line-0 frontmatter** | Page properties (`tags::`, `alias::`, `title::`, …) live at the **absolute top** of the file as raw `key:: value` lines **without** bullet dashes (`- `). A blank line separates frontmatter from the first bullet. |
| **Block properties** | Block-scoped properties (`id::`, `matryca-plumber::`, …) sit **immediately under the parent bullet**, indented **+2 spaces**, **before** child bullets or multiline continuations. Never orphan or delete existing `id::` lines. |
| **Multiline blocks** | Shift+Enter continuations use `indent + 2 spaces` (`bullet_indent_unit()`). Property insertion must respect continuation lines before child bullets (`block_property_insert_index()`). |
| **Windows `\r\n` stripping** | All scanners normalize with `strip_line_endings()` / `rstrip("\r\n")` before regex matching. Writes emit `\n` via `canonical_line_suffix()` — never reintroduce `\r\n` on output. Mixed line endings must not break fence detection or block-span math. |
| **Dead zones** | Never mutate lines inside fenced code blocks, HTML comments, or `#+BEGIN_QUERY` … `#+END_QUERY` regions (`global_fence_scanner.py`). |

When in doubt: `read_graph_data` with `dry_run: true` on mutators first.

### Phase 4 — No central DB (JSON ledger only)

Matryca tracks daemon progress in a **local JSON ledger** at the graph root — not in a database server.

| File | Role |
|------|------|
| **`.matryca_daemon_state.json`** | AI ledger + checkpoint plane (processed files, bootstrap phase, token telemetry, quarantine flags). Written atomically (tmp → fsync → `os.replace`). |
| **`.matryca_xray_state.json`** | Session alias map (`[n]` → block UUID) for X-Ray mode. |

**Forbidden:** SQLite, Postgres, Redis, or any hosted DB as system-of-record for graph content or daemon state.

Optional git snapshots on the graph repo are fine; they remain files on disk.

---

## Local development with `uv`

1. **Python 3.12+** (see `.python-version`).
2. Install **[uv](https://docs.astral.sh/uv/)**.
3. From the repository root:

   ```bash
   make install
   ```

   This runs `uv sync --extra dev` and creates `.venv/`.

4. Optional: activate the venv or use `uv run` / Makefile targets.

   ```bash
   source .venv/bin/activate
   ```

5. For integration work, copy env defaults:

   ```bash
   cp .env.example .env
   ```

   Set **`LOGSEQ_GRAPH_PATH`** to your Logseq graph root (folder containing `pages/`). Matryca is headless — no Logseq desktop app required for most tests.

6. List Make targets:

   ```bash
   make help
   ```

### Makefile targets

| Target | What it does |
|--------|----------------|
| `make install` | `uv sync --extra dev` |
| `make format` | Ruff auto-fix + format |
| `make lint` | Ruff lint only |
| `make typecheck` | `mypy src/ tests/` (strict) |
| `make test` | `pytest -q` |
| **`make check`** | **`format` → `lint` → `typecheck` → `test`** (full local gate) |
| `make clean` | Remove `.venv`, caches |

### Frontend (React cockpit)

```bash
cd frontend
npm ci
npm run build
```

CI builds the SPA before running `make check`.

---

## Merge bar: green `make check`

**No pull request is merged unless `make check` is 100% green.**

That means, in order:

1. **Ruff** — auto-fix and format the tree, then lint clean
2. **Mypy** — strict type-check on `src/` and `tests/`
3. **Pytest** — full suite (**392+** tests; currently **394** collected)

GitHub Actions on pushes and pull requests to **`main`** runs the same gate (see [`.github/workflows/ci.yml`](.github/workflows/ci.yml)): `uv sync`, frontend `npm ci` + `npm run build`, then `make check`. **Any failing test blocks merge.**

Never commit secrets (no `.env`, tokens, or private graph paths in git).

**Background service:** `matryca service install` must target a **stable** binary (for example after `uv tool install matryca-plumber`). Do not install the daemon from ephemeral `uvx` — see [README.md](README.md#background-service-matryca-service--persistent-install-only).

---

## Writing tests for new MCP tools

### Stack conventions

- **FastMCP** — Tools are async functions registered with `@mcp.tool()` in `register_mcp_tools` (`src/agent/mcp_server.py`). Test the logic the tool calls; you usually do not need stdio MCP in tests.
- **Pydantic** — Cover models with `model_validate` / `ValidationError` where rules apply.
- **pytest-asyncio** — `asyncio_mode = auto` in `pyproject.toml`. Use `@pytest.mark.asyncio` when awaiting bridge methods.

### Recommended patterns

1. **Model-only tests** — Fast, no I/O. Example: outline schema rules in `tests/test_mcp_server.py`.
2. **Stub `LogseqClient`** — Monkeypatch bridge methods to record arguments. See `test_write_logseq_outline_chains_parent_uuids`.
3. **Filesystem fixtures** — Use `tmp_path`, set `LOGSEQ_GRAPH_PATH` via `monkeypatch.setenv`, call `src/graph/` directly.
4. **Thin MCP wrapper, fat module** — Implement in `src/graph/` or `src/agent/`, unit-test helpers, keep `@mcp.tool()` bodies short.

### Tool design checklist

- Prefer explicit typed parameters; use `dict[str, Any]` only where MCP JSON must stay flexible.
- For mutators, default `dry_run=true` when behavior could touch many files.
- `src/` must satisfy **strict mypy**; tests may relax annotations per Ruff `per-file-ignores` for `tests/**`.

When you add or change a tool, **extend or add tests under [`tests/`](tests/)** so behavior is pinned before review.

---

## Pull request workflow

1. **Fork** the repository and use a **focused** branch per change.
2. **Open or reference an issue** for larger features so design stays aligned with the Phase 0–4 rules.
3. Describe **why** the change exists and any trade-offs in the PR body.
4. Confirm **`make check`** passes locally.
5. Use the PR template checklist (OCC, CRLF, `make check`).

---

## Reporting bugs

Include OS, Logseq version, LM Studio model, Plumber version, and **zipped Loguru logs** from `logs/matryca_plumber.log` (rotated archives are `.zip` files in the same directory). See the [bug report issue template](.github/ISSUE_TEMPLATE/bug_report.yml).

---

## Code of conduct

Be respectful, assume good intent, and keep feedback actionable. We want contributors of all backgrounds to feel welcome.
