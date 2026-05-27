# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Auto `.env` provisioning** — `ensure_repo_dotenv_from_example()` copies `.env.example` → `.env` on first startup (CLI, UI lifespan, `reload_plumber_dotenv`) with a clear Loguru info line.
- **Pre-flight API & wizard** — `GET /api/preflight` validates graph path, L1 memory, and local LLM `/v1/models`; Sovereign UI modal blocks **Start Engine** until all checks pass. Step 3 includes Matryca.ai mission copy, May 2026 CPU model recommendations, and MoE hardware guidance.
- **Runtime bootstrap** (`src/utils/runtime_bootstrap.py`) — `prepare_matryca_runtime()` provisions log directories, sibling `matryca-l1/`, `.matryca_semantic_cache/`, `templates/`, and seeds `matryca-wiki.yml` before harvest or MCP lifecycles (daemon, CLI, Sovereign UI, MCP stdio). Spec: [`docs/openspec/runtime-bootstrap.md`](docs/openspec/runtime-bootstrap.md).
- **L1 directory provisioning** — `ensure_matryca_l1_dir()` creates `<parent-of-vault>/matryca-l1/` with operator docs (`README.md`, not loaded into LLM context) and starter `session-rules.md` when no other content `*.md` exists; override via `MATRYCA_L1_PATH` or `memory_path` in wiki YAML.
- **CI test workflow** (`.github/workflows/test.yml`) — Pytest, Ruff, and Mypy on `main` and pull requests (with Sovereign UI frontend build).

### Changed

- **Loguru bootstrap** — `configure_loguru()` delegates log parent-dir creation to the same runtime bootstrap helper as ops JSONL sinks.
- **`.env.example`** — documents `MATRYCA_L1_PATH`, log path overrides, and runtime layout pointers.

### Fixed

- **Sovereign UI polling** — `GET /api/state` returns only the daemon checkpoint (no full-graph scan); topology telemetry moves to async `GET /api/graph-analytics` via `asyncio.to_thread`, so the 1s poll loop no longer blocks the FastAPI event loop.
- **Phase 1 progress** — bootstrap harvest persists `bootstrap_scanned` / `bootstrap_total` every 50 pages; the control-room progress bar advances during cataloging instead of staying at 0%.
- **CLI logging** — reject or redact operator payloads that would log secrets in clear text (`secret_violations_in_text` on CLI paths).

## [1.6.1] - 2026-05-25

No user-facing changes (version alignment with PyPI / lockfile).

## [1.6.0] - 2026-05-25

### Added

- **Shared LLM SSRF policy** (`src/utils/llm_url_policy.py`) — `validate_llm_proxy_url()` guards Sovereign UI model discovery, `.env` persistence, and daemon `InstructorLLMClient` outbound calls (metadata IPs, non-HTTP schemes, hostile DNS).
- **Graph path allowlist** — `validate_logseq_graph_path_for_config()` restricts `LOGSEQ_GRAPH_PATH` updates from the Settings UI to home, repo, temp, current graph, and optional `MATRYCA_ALLOWED_GRAPH_ROOTS`.
- **Split UI rate limits** — `MATRYCA_UI_RATE_LIMIT_UNAUTH_PER_MINUTE` (default 30) for anonymous `/api/*` traffic; authenticated budget remains `MATRYCA_UI_RATE_LIMIT_PER_MINUTE` (default 120). `/api/health` and loopback-only `/api/auth/session` are exempt.
- **`MATRYCA_MCP_ENABLED`** — FastMCP stdio is **off by default**; bare `matryca-plumber` exits with guidance until the flag is set (Claude Desktop / Cursor hosts).

### Changed

- **MCP tool errors** — `mcp_tool_guard` returns sanitized messages (no raw filesystem paths) unless `MATRYCA_DEBUG=true`.
- **Sovereign UI default port** — aligned dev API base and Uvicorn default to **8500** (was 8000 in some paths).
- **Sovereign UI frontend** — rebuilt production bundle shipped in the PyPI wheel.

## [1.5.17] - 2026-05-24

### Changed

- **Security modules** — consolidated regex policies and secret-redaction helpers for stricter typing and reuse across CLI, UI, and daemon surfaces.

## [1.5.16] - 2026-05-24

### Changed

- **`uv.lock`** — synced for CI reproducibility (no application logic changes).

## [1.5.15] - 2026-05-24

### Fixed

- **MCP log bridge** — reset/re-register Loguru MCP telemetry sink after `logger.remove()` (fixes flaky `test_mcp_telemetry` under full pytest collection).
- **Sovereign UI daemon start** — treat successful detached launcher exit (code 0) as success when a live PID is published.
- **Optimistic concurrency** — capture OCC baseline before page reads; re-baseline after cognitive lint self-writes; re-check mtime immediately before atomic commit.
- **`plumber_entry`** — lazy-import MCP entrypoint so CLI routing does not load FastMCP at import time.
- **Page lock registry** — LRU eviction of unlocked entries instead of clearing the entire registry at 4096 entries.
- **`.env` persistence** — atomic writes from the Sovereign UI settings drawer.
- **UI auth session** — restrict `/api/auth/session` to loopback clients unless `MATRYCA_UI_ALLOW_LAN=1`; refuse `0.0.0.0` bind without that flag.
- **Daemon PID handling** — return `foreign_pid` when a live non-plumber process holds the PID file; tighten `is_plumber_process` heuristics.
- **Frontend auth** — validate session tokens, fail fast on bootstrap errors, default production API base to `window.location.origin`, polyfill `AbortSignal.any`.

## [1.5.14] - 2026-05-24

### Changed

- **MCP telemetry** — clearer context management in structured MCP log events.

## [1.5.13] - 2026-05-24

### Fixed

- **MCP Loguru sink** — thread-safe `enqueue` pickling for telemetry under pytest and multi-threaded hosts.

## [1.5.12] - 2026-05-24

### Added

- **`matryca-plumber` console router** — route shorthand CLI invocations (`status`, `start`, …) to `matryca plumber` while preserving MCP stdio as the default.

## [1.4.1] - 2026-05-20

### Added

- **`search_graph` / `method=resolve_entity`** — vault-wide alias index resolution via `cached_build_alias_index` (canonical page, collisions, `safe_to_create_new_page`).
- **X-Ray alias support in `read_graph_data` / `block_ast`** — `Page Title|[n]` resolves through `.matryca_xray_state.json` before disk lookup.

### Changed

- **`mutate_graph` / `write_outline`** success responses now include `"ok": true` for a uniform JSON contract.
- **Routing hints** for entity outlines point agents to `search_graph` / `resolve_entity` instead of a removed standalone tool.
- **`.env.example`** — removed obsolete `LOGSEQ_API_*` variables (headless-only since v1.4.0).

### Removed

- **`src/bridge/`** — empty legacy package left after the HTTP client purge.

## [1.4.0] - 2026-05-19

### Added

- **FastMCP integration** — MCP server (`FastMCP`) with stdio transport, lifespan wiring, and five mega-tools (`src/main.py`).
- **Makefile developer experience** — targets for install (`uv`), format, lint, typecheck, test, aggregate `check`, and clean (`Makefile`).
- **GitHub Actions CI** — workflow running Ruff, Mypy, and Pytest on push and pull request to `main` (`.github/workflows/ci.yml`).
- **Pydantic data validation** — hierarchical `OutlineNode` models and validated tool payloads (`src/agent/mcp_server.py`).
- **Apache License 2.0** — project licensing as declared in `LICENSE` and `pyproject.toml`.

### Removed

- **Logseq HTTP JSON-RPC client** — `httpx` / `LogseqClient` / `src/bridge/logseq_client.py` (100% headless disk writes).
