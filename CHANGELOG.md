# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
