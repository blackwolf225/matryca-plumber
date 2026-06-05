# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.9.2] - 2026-06-05

### Added

- **Agent onboarding (`llms.txt`)** — `.well-known/llms.txt` standard for autonomous agents (Cursor, Claude Code, Windsurf, Hermes): zero-shot `uvx matryca-plumber` examples, `LOGSEQ_GRAPH_PATH` (no `--graph`), verified `--json read` / `context load` / `plumber audit`, FastMCP stdio (`MATRYCA_MCP_ENABLED`), and anti-patterns to avoid local CLI hallucinations; root `llms.txt` mirror; README agent hook updated.

### Changed

- **Documentation (v1.9.2)** — Aligned README, ARCHITECTURE, PROJECT_DIARY, CONTRIBUTING, SECURITY, SYSTEM_PROMPT, and OpenSpec index with `llms.txt` agent onboarding; added [`docs/openspec/agent-onboarding.md`](docs/openspec/agent-onboarding.md); RELEASE_PROCESS/BRANDING cross-links; test count badges updated to 610+.
- **Dependabot lockfile sync** — `.github/workflows/dependabot-uv-fix.yml` runs `uv lock` on Dependabot PRs and pushes `uv.lock` fixes so CI stays green.
- **README** — Restructured agent/web-scraper entry to prefer PyPI `uvx matryca-plumber` over `git clone`.
- **Dependencies** — Routine bumps: `openai`, `rich`, `packaging`, `mypy`, `pytest-cov` (Dependabot).

### Security

- **Transitive `aiohttp`** — `uv.lock` pins `aiohttp` ≥3.14.0 to remediate upstream CVEs pulled via the dependency tree (Dependabot #5, #6).
- **CLI stdout / CodeQL** — Cleared clear-text-logging false positives: transport layer documents intentional `sys.stdout` use; machine output stays secret-sanitized via `redact_secrets_in_text` and targeted suppressions (`safe_str` helper).

## [1.9.1] - 2026-06-01

### Changed

- **Link verification** — Ruff formatting and minor readability in `src/graph/link_verification.py` and `src/semantic/store.py`; registry batch tests use consolidated mock patches (`tests/test_link_verification.py`).

## [1.9.0] - 2026-06-01

### Added

- **Structural link verification (#15)** — Passive extract of `http(s)://` URLs and local `assets/` paths into `.matryca_link_registry.json`; async HTTP HEAD + filesystem checks on the daemon duty cycle; OCC-safe `dead-link::` / `missing-asset::` block properties after repeated failures (`src/graph/link_verification.py`).
- **Agent-centric DX (#16)** — Global CLI `--json` for machine-readable stdout; `matryca context load` semantic macro; `read subtree` for focused block/header extracts; Journey Log appends `## 🤖 Matryca Activity` to today's journal after each duty cycle (`src/cli/__init__.py`, `src/agent/journey_log.py`, `src/agent/context_load.py`).
- **Documentation (v1.9)** — OpenSpec [`docs/openspec/link-verification.md`](docs/openspec/link-verification.md) and [`docs/openspec/agent-dx.md`](docs/openspec/agent-dx.md); ARCHITECTURE/README/SYSTEM_PROMPT/PROJECT_DIARY aligned with mermaid diagrams for link hygiene and agent DX.
- **Dual embedding strategy (Phase 3)** — Applicability synthesis + dual vectors per block (`vec_content`, `vec_applicability`) in `.matryca_semantic_cache/block_vectors.json`; hybrid cosine retrieval via `search_graph` / `method=semantic`; daemon indexing gated by `MATRYCA_DUAL_EMBEDDING_ENABLED` (`src/semantic/`, `docs/openspec/dual-embedding.md`).
- **Atomic document ingestion (Phase 2)** — **`ingest_document`** MCP tool parses external markdown via OS temp files (never under `pages/`), stamps fresh block UUIDs, appends to daily `Ingest/YYYY-MM-DD` or `MATRYCA_INGEST_PAGE`, and updates `LOG` / `GLOSSARY` ledgers with OCC-safe writes (`src/agent/ingestion.py`, `docs/openspec/ingest.md`).
- **Telos & Identity layer** — In-graph persona on `matryca/config` or `matryca-config` (`- # Telos`, `- # AI Constraints`); reactive refresh via AST cache + file watcher; LLM system-prompt injection; MCP identity footer; **`store_fact`** MCP tool appends durable preferences under AI Constraints on `pages/matryca-config.md` (`src/daemon/config_layer.py`, `src/agent/memory_tools.py`, `docs/openspec/identity-config.md`).
- **Reactive daemon file watching** — `watchdog` observer on `pages/` and `journals/` with debounced change detection (`MATRYCA_WATCH_DEBOUNCE_MS`) wakes the maintenance duty cycle instead of waiting only on poll interval (`src/daemon/file_watcher.py`).
- **In-memory AST cache** — `LogseqGraph` bootstrap and per-file `invalidate_and_reload_page` deltas for MCP/daemon reads (`src/daemon/ast_cache.py`).
- **Surgical robot git commits** — Post-write GitPython commits stage only the modified `.md` file(s) with `robot(matryca): AI auto-update - …` messages; on by default when the graph root is a git repo (`MATRYCA_GIT_ROBOT_COMMIT`, `src/daemon/git_audit.py`).
- **Sovereign UI settings** — Infrastructure drawer exposes `LLM_API_KEY` as **API Token** (password field); persisted to `.env` on save. Required only for cloud OpenAI-compatible endpoints.

### Fixed

- **Journey log pending leak** — After appending `## 🤖 Matryca Activity` to today's journal, the daemon records `journals/YYYY_MM_DD.md` in file state so `list_pending_files` does not re-queue it on the next cycle (`src/agent/maintenance_daemon.py`).
- **Link verification hygiene** — Re-check flagged registry entries; GET fallback when HEAD is inconclusive; merge-safe registry persistence; prune removed page links; clear on-graph `dead-link::` / `missing-asset::` on recovery; journey log splits URL vs asset flag counts (`src/graph/link_verification.py`, `src/agent/maintenance_daemon.py`).
- **Dual embedding durability** — `block_vectors.json` uses cross-process flock + atomic write, survives `clear_semantic_cache`, prunes stale block UUIDs per page, validates embedding dimensions, caps search scan via `MATRYCA_SEMANTIC_SEARCH_MAX_CANDIDATES` (`src/semantic/`).
- **`context load` subtree** — Subtree reads run in a worker thread; invalid `Page|uuid` queries return structured errors instead of raising (`src/agent/context_load.py`).
- **Second-pass hygiene** — Link recovery waits for successful on-graph property clear; block-vector cache reloads when `block_vectors.json` mtime changes; indexer prunes vectors for empty/missing AST pages; metrics workflow uses strict JSON parse and timezone-aware dates (`.github/workflows/metrics-saver.yml`).
- **Third-pass hardening** — Idempotent link flag when hygiene property already exists; bounded GET fallback (404→GET); no strike inflation on already-flagged rows; registry purge when page file deleted; AST-miss indexing skips prune; vector save under instance lock; semantic search cap prefers newest blocks (`src/graph/link_verification.py`, `src/semantic/`).
- **Fourth-pass hardening** — Indexer keeps vectors on transient embed failures; link registry purge on watcher `deleted`; canonical AST page keys for `block_vectors.json`; lexical pre-filter before semantic search cap; bounded GET with range + explicit close; empty-page semantic apply records `skipped` (`src/semantic/`, `src/agent/maintenance_daemon.py`).

### Changed

- **Documentation** — OpenSpec, `SYSTEM_PROMPT.md`, `README.md`, `ARCHITECTURE.md`, `PROJECT_DIARY.md`, and roadmaps aligned for seven MCP tools (`ingest_document` + `store_fact`).
- **Git audit trail** — Retired pre-write `MATRYCA_GIT_SNAPSHOT_ON_WRITE` / `git add -A` snapshots; robot commits run after successful atomic writes via post-write hooks.

### Removed

- **`src/agent/git_snapshot.py`** — Replaced by `src/daemon/git_audit.py` post-write commits.

### Security

- **CLI stdout sanitization** — Machine output masks OpenAI (`sk-`), Anthropic (`sk-ant-`), Bearer, and Logseq credential properties in-place via `redact_secrets_in_text` instead of replacing entire payloads; CodeQL `py/clear-text-logging-sensitive-data` suppressions document stdout as the intentional CLI channel (`src/cli/__init__.py`).

## [1.8.5] - 2026-05-29

### Changed

- **`.env.example`** — Every tunable key documents **Default (code)** vs **Template** values; fixed `MATRYCA_PLUMBER_COMPRESSION_TRIGGER_TOKENS` to `100000`; added `MATRYCA_PLUMBER_NICE_LEVEL`, `MATRYCA_PLUMBER_IONICE_IDLE`, LLM/service-manager notes; `MATRYCA_LLM_PROMPT_CACHE_MODE` marked reserved. CI: `tests/test_env_example_coverage.py`.
- **Cursor rule `07-env-example.mdc`** — Agents must update `.env.example` when env vars change; file split into **Operator essentials** vs **Advanced / high impact** sections.

### Fixed

- **v1.8 audit (round 4)** — `generate_graph_insights` is stateless so ontology reports do not pollute Ermes history; context-compression summaries are prose-sanitized before persistence; semantic-index block catalogs cap at 8k chars; Phase 2 LLM inference no longer holds `page_rmw_lock` (write-only lock in `apply_semantic_page_result`); `id::` lines are excluded from property-line hygiene so Logseq block UUIDs are never edited as properties.
- **Gemma JSON degeneration** — Structured LLM completions cap at `MATRYCA_LLM_MAX_COMPLETION_TOKENS` (default 2048); `json_repair` uses balanced-brace extraction (not greedy `{.*}`), strips post-`}` `\n` token loops, and normalizes Gemma `\n  \"key` leakage before indexing Logseq pages.
- **LLM resilience audit** — Context compression now uses `MATRYCA_LLM_MAX_COMPRESSION_TOKENS`; prose/markdown completions sanitized; Ermes history turns cleaned before append; balanced `[` `]` extraction; collapse of `\t`/`\"` repetition loops; debug NDJSON gated behind `MATRYCA_LLM_DEBUG_JSON`.
- **LLM resilience (round 2)** — Unbalanced/truncated JSON recovery; MCP `parse_json_object` uses `loads_repaired_json`; Path B correction errors stripped of degeneration; cluster focus capped via `MATRYCA_CLUSTER_FOCUS_MAX_CHARS`.
- **Semantic cache hygiene** — `validate_cached_model` evicts schema-invalid or oversize `.matryca_semantic_cache` entries instead of replaying poisoned LLM JSON into the graph pipeline.

### Added

- **Docs** — [`docs/resilience-llm-json-triz.md`](docs/resilience-llm-json-triz.md): TRIZ / resilience-engineering narrative for local LLM JSON (Gemma tail of death, defense-in-depth layers, verification).

## [1.8.4] - 2026-05-29

### Changed

- **README** — Expanded professional badge block at the top (PyPI, GitHub Release, CI quality gates, platform, MCP, Logseq OG, security, contributing, code of conduct).

### Fixed

- **CI** — Pin `astral-sh/setup-uv` to immutable `v8.1.0` (major tag `@v8` was removed in setup-uv v8.0.0).

## [1.8.3] - 2026-05-29

### Fixed

- **CI** — `ruff format` on `maintenance_daemon.py`; GitHub Actions upgraded to Node 24–compatible action majors (`checkout@v6`, `setup-node@v6`, `setup-uv@v8`).

## [1.8.2] - 2026-05-28

### Changed

- **`logseq-matryca-parser`** — minimum dependency raised to **1.1.1** (latest on PyPI; was `>=0.3.3`).

### Fixed

- **Cognitive KV-cache alignment** — `run_cognitive_lint_pipeline` rebuilds `PagePromptSession` after on-disk mutations so semantic index LLM calls no longer use a stale stable prefix.
- **Master catalog load safety** — transient `OSError` no longer caches an empty catalog that could overwrite `master_catalog.json`; corrupt JSON is quarantined or restored from `.bak`; `save()` is blocked until a successful load.
- **Phase 2 page locking** — daemon holds `page_rmw_lock` through cognitive lint, LLM inference, and apply (replacing probe-only locking); in-process lock is re-entrant so nested module writes do not deadlock.
- **Bootstrap failure state** — `bootstrap_failed` persisted in daemon checkpoint; Phase 2 LLM cycles are skipped until Phase 1 succeeds.
- **LLM transport retries** — exponential backoff on transient HTTP errors (`MATRYCA_LLM_TRANSPORT_RETRIES`, default 3).
- **CPU affinity parsing** — invalid `MATRYCA_PLUMBER_CPU_AFFINITY` tokens are logged and skipped instead of crashing startup.
- **`nice_applied` telemetry** — set only when `os.nice` succeeds.

### Security

- **UI token hardening** — startup warning when `MATRYCA_UI_TOKEN` is unset; optional `MATRYCA_UI_REQUIRE_EXPLICIT_TOKEN` refuses UI without an explicit token; `SECURITY.md` / `.env.example` document MCP trust boundary and loopback session risk.

## [1.8.1] - 2026-05-28

### Fixed

- **CI formatting** — `ruff format` on `page_prompt_session.py`, `process_priority.py`, and `master_catalog.py` so `make ci` passes on `main`.

## [1.8.0] - 2026-05-28

### Added

- **v1.8 edge software plan** — [`docs/v1.8-SOFTWARE-EDGE-PLAN.md`](docs/v1.8-SOFTWARE-EDGE-PLAN.md): CPU sandbox, frozen KV prefix, adaptive structured output, mmap reads.
- **Adaptive LLM client** — [`src/agent/llm_client.py`](src/agent/llm_client.py): capability probe, logits JSON-schema fast path, 3-try validation self-correction on legacy servers, `StructuredOutputExhaustedError`.
- **Frozen prompt prefix** — `FrozenPromptPrefix` + SHA-256 verify before LLM calls; `kv_prefix_hash` in ops JSONL.
- **CPU sandbox** — `MATRYCA_CPU_SANDBOX`, optional `MATRYCA_PLUMBER_CPU_AFFINITY`; `psutil` via `[edge]` extra.
- **Mmap graph reads** — [`src/graph/markdown_io.py`](src/graph/markdown_io.py) for Phase 1 bootstrap regex path (`MATRYCA_GRAPH_READ_MMAP`).
- **v1.8 edge computing documentation** — [`docs/v1.8-OPTIMIZATION-PLAN.md`](docs/v1.8-OPTIMIZATION-PLAN.md), [`docs/openspec/llm-performance.md`](docs/openspec/llm-performance.md), ARCHITECTURE / PROJECT_DIARY / README updates.
- **PagePromptSession** — stable per-page LLM prefix reused across cognitive tasks; alias map in capped user block (`MATRYCA_ALIAS_PROMPT_MAX_CHARS`), not system prompt.
- **Stable semantic system prompt** — `semantic_lint_prompts.py` for KV-friendly compiler rules shared by index + cognitive pipeline.
- **Backlink index** — persisted `.matryca_semantic_cache/backlink_counts.json` replaces full-graph rescans during bootstrap.
- **Memory budget** — `release_phase1_memory()`, RSS snapshots (`MATRYCA_RAM_BUDGET_MB`), semantic cache in-process LRU.
- **Cooperative yield** — `yield_host()` during bootstrap; env-tunable intervals and I/O batch pauses.
- **Synthetic graph script** — `scripts/gen_synthetic_graph.py`; slow tests via `make perf` (`pytest -m slow`).

### Changed

- **Documentation** — README, ARCHITECTURE, PROJECT_DIARY, openspec, and v1.8 plans aligned to **1.8.0**; `.env.example` marks legacy `MATRYCA_LM_INSTRUCTOR_*` vars as deprecated (probe-driven `llm_client` Path A/B).
- **Bootstrap harvest** — `build_cache_aligned_prompt` for `harvest_page_summary` and MapReduce reduce; `stateless=True` on per-page LLM paths.
- **BM25 corpus** — postings-lite `doc_term_freqs` (lower RAM); `MATRYCA_BM25_MODE=resident|ondemand`; `release_bm25_corpus()` on Phase 1 teardown.
- **Semantic cache purge** — TTL sweep skips `master_catalog.json`, `backlink_counts.json`, and `semantic_clusters.json`.
- **Daemon** — post-bootstrap `release_phase1_memory()`, cluster precompute after Phase 1, `apply_cpu_sandbox()` / `apply_plumber_priority`, LLM `probe_backend()` at foreground start, `MATRYCA_BOOTSTRAP_CHECKPOINT_EVERY`.
- **Structured output** — `InstructorLLMClient` moved to `llm_client.py`; instructor mode carousel replaced by probe-driven Path A/B.

### Fixed

- **Semantic cache TTL** — no longer deletes the master catalog when purging expired inference cache files.

## [1.7.5] - 2026-05-27

### Added

- **Concurrency preflight** — `probe_concurrency_capability()` and a Sovereign UI checklist row for cross-process `flock` vs in-process-only mode; daemon logs the active contract at startup.
- **`outline_models.py`** — shared `OutlineNode` validation for MCP and `graph_dispatch` (breaks circular import).
- **Tests** — `json_flock`, semantic cache router, page lock probe, bounded JSON ints, LAN UI token policy, in-root symlink sandbox cases.

### Changed

- **Lock-before-LLM** — daemon probes `page_rmw_lock` before paid inference; `lock_backoff` ledger status with exponential retry instead of infinite re-inference.
- **Page lock registry** — refuses growth past 4096 entries (`PageLockUnavailableError`).
- **Semantic cache** — disk read/write wrapped in `cross_process_json_flock`.
- **Path sandbox** — symlinks allowed when resolved target stays under the graph root; `read_graph_file_text` defaults to strict UTF-8.
- **Graph markdown I/O** — `markdown_blocks` reads/writes use strict UTF-8 for vault content.
- **Sovereign UI API** — blocking routes offloaded with `asyncio.to_thread`; daemon start/stop no longer block the event loop; `MATRYCA_UI_ALLOW_LAN` requires an explicit `MATRYCA_UI_TOKEN`.
- **CI** — single `ci.yml` workflow with `make ci` (`ruff format --check` without mutating the tree); Ruff `ASYNC`/`S`/`PERF`/`RUF`; pytest coverage gate (70% on `src`).

### Fixed

- **`graph_dispatch`** — safe integer parsing for JSON tool options (no bare `ValueError` escapes).
- **Phase 2 progress bar (Sovereign UI)** — vault-wide and per-cluster progress now share one resolver with the TUI and daemon checkpoints (`progress_*` on `GET /api/state`); persisted `phase2_cognitive_*` counters and in-flight cluster file subtitles so the bar no longer stays at 0% while the engine works.

## [1.7.0] - 2026-05-27

### Added

- **Pre-flight onboarding (graph + L1)** — Sovereign UI checklist step 2 saves the Logseq test vault path inline; step 3 **Create matryca-l1 folder** calls `POST /api/provision-l1` to provision sibling `matryca-l1/` (README + `session-rules.md`, wiki `memory_path` sync). Template `MATRYCA_L1_PATH` values from `.env.example` are ignored and cleared on provision.
- **Auto `.env` provisioning** — `ensure_repo_dotenv_from_example()` copies `.env.example` → `.env` on first startup (CLI, UI lifespan, `reload_plumber_dotenv`) with a clear Loguru info line.
- **Pre-flight API & wizard** — `GET /api/preflight` validates graph path, L1 memory, and local LLM `/v1/models`; Sovereign UI modal blocks **Start Engine** until all checks pass. Step 3 includes Matryca.ai mission copy, Qwen 3.5 (4B / 1.7B Instruct) sizing, Ministral 3 (3B), and MoE hardware guidance.
- **Branding guide** — [`docs/BRANDING.md`](docs/BRANDING.md): product name **Matryca Plumber** (not “Matryca” alone), Matryca.ai attribution; README, CONTRIBUTING, and pre-flight UI aligned.
- **Runtime bootstrap** (`src/utils/runtime_bootstrap.py`) — `prepare_matryca_runtime()` provisions log directories, sibling `matryca-l1/`, `.matryca_semantic_cache/`, `templates/`, and seeds `matryca-wiki.yml` before harvest or MCP lifecycles (daemon, CLI, Sovereign UI, MCP stdio). Spec: [`docs/openspec/runtime-bootstrap.md`](docs/openspec/runtime-bootstrap.md).
- **L1 directory provisioning** — `ensure_matryca_l1_dir()` creates `<parent-of-vault>/matryca-l1/` with operator docs (`README.md`, not loaded into LLM context) and starter `session-rules.md` when no other content `*.md` exists; override via `MATRYCA_L1_PATH` or `memory_path` in wiki YAML.
- **CI test workflow** (`.github/workflows/test.yml`) — Pytest, Ruff, and Mypy on `main` and pull requests (with Sovereign UI frontend build).
- **Phase 1 catalog pills** — bootstrap harvest persists `bootstrap_recent` (per-page harvest status) so the control room shows live indexing pills during cataloging, not only Phase 2 checkpoints.
- **Page Summaries metric** — `GET /api/graph-analytics` exposes `page_summaries` (master catalog + session ledger); Sovereign UI **Plumber Agent Cognition** panel shows a fourth tile.

### Changed

- **Pre-flight & docs** — Sovereign UI wizard and README recommend only **Gemma 4-E4b Instruct** (`gemma-4-e4b-it`); removed Qwen/Ministral model lists; note on testing additional models for CPU-only 16 GB RAM. `.env.example` default updated to match.
- **README** — documents Sovereign UI pre-flight checklist (operator steps, live checks, `status` vs `start`, `uvx` zero-install), Marco Porcellato · Matryca.ai attribution, and links to `docs/BRANDING.md`.
- **Loguru bootstrap** — `configure_loguru()` delegates log parent-dir creation to the same runtime bootstrap helper as ops JSONL sinks.
- **`.env.example`** — `MATRYCA_L1_PATH` left commented (sibling `matryca-l1/` via pre-flight); documents log path overrides and runtime layout pointers.

### Fixed

- **Phase 1 catalog pills (empty state)** — pills no longer read only `state.files` during Phase 1 when the daemon has not yet started Phase 2 file checkpoints.
- **Phase 1 thermal delay** — bootstrap pauses reload `MATRYCA_THERMAL_DELAY_BOOTSTRAP` from `.env` after every catalog LLM turn (Settings Drawer value is honored); cool-down sleeps wake promptly on Stop.
- **Phase 1 cooperative stop** — bootstrap harvest checks shutdown between pages and during map-reduce chunks instead of running the full vault after Stop.
- **Sovereign UI Stop** — `POST /api/daemon/stop` is exempt from UI rate limiting; the 1s poll loop no longer hammers `/api/config`, avoiding 429 responses that blocked stop requests.
- **Pre-flight graph save** — `POST /api/config/graph-path` (and ``PATCH``) updates only ``LOGSEQ_GRAPH_PATH``; API errors surface in the UI; verified graph clears stale save errors.
- **Sovereign UI start gate** — `GET /api/state` reports `stopped` when no live Plumber PID is present, so opening `status` alone does not imply the engine is running or disable **Start Engine** on a stale `idle` checkpoint.
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
