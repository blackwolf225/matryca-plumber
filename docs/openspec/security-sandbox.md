# Security & Sandbox (v1.9.9)

**Milestone:** v1.9.9 — Security & Sandbox (v1.9.x perfection track)  
**Implementation:** [`src/graph/path_sandbox.py`](../../src/graph/path_sandbox.py), [`src/utils/bounded_json.py`](../../src/utils/bounded_json.py), [`scripts/check_graph_read_sandbox.py`](../../scripts/check_graph_read_sandbox.py)  
**Operator matrix:** [`SECURITY.md`](../../SECURITY.md)

v1.9.9 closes the pre-v2.0 **Security & Sandbox** milestone: every graph-local read path is sandbox-validated, JSON checkpoints are size-bounded, and CI blocks new `Path.read_text()` bypasses in graph/agent/rag code.

---

## Path sandbox (reads and writes)

All candidate paths under `LOGSEQ_GRAPH_PATH` are resolved with `Path.resolve()` and checked with **`is_relative_to(graph_root)`** before I/O.

| Primitive | Role |
|-----------|------|
| `assert_path_within_graph` | Raises `PathTraversalSecurityError` on escape |
| `read_graph_file_text` | Read UTF-8 only after sandbox pass |
| `read_graph_page_text` | Sandbox + optional mmap (`markdown_io.py`) |
| `resolve_graph_relative_key` | Map registry keys back under the graph root |

**v1.9.9 hardening:**

- **Link verification** — `_resolve_asset_path` and `.matryca_link_registry.json` `page_relpath` values are validated before read; traversal refs and tampered registry rows are treated as missing/invalid ([`link-verification.md`](link-verification.md)).
- **wiki_lint** — `is_scannable_graph_markdown()` skips symlink escape under flat `pages/*.md`.
- **Defense-in-depth** — graph/agent/rag modules use `read_graph_file_text()` instead of raw `Path.read_text()`; `make sandbox-read-check` enforces this in CI.

---

## Bounded JSON checkpoints

Graph-local JSON files (catalog, link registry, daemon state, semantic cache, block vectors) load through **`read_bounded_json()`** with env **`MATRYCA_JSON_MAX_BYTES`** (default **64 MiB**). Oversized files fail fast instead of causing local memory DoS.

---

## Debug log and UI token policy

| Variable | v1.9.9 behavior |
|----------|-----------------|
| `MATRYCA_LLM_DEBUG_LOG_PATH` | Must lie under allowed roots (`config_paths`); secrets redacted in NDJSON when log redaction is on |
| `MATRYCA_UI_REQUIRE_EXPLICIT_TOKEN` | `.env.example` **template** is `true` — new installs must set `MATRYCA_UI_TOKEN`; runtime default when unset remains permissive for legacy `.env` files |

Ephemeral auto-generated UI tokens are still exposed on loopback via `/api/auth/session`; set an explicit token on shared hosts.

---

## Contributor gate

```bash
make sandbox-read-check   # scripts/check_graph_read_sandbox.py
make ci                   # format-check + lint + typecheck + sandbox-read-check + test (GitHub Actions)
```

New graph reads in `src/graph/`, `src/agent/`, `src/rag/`, or `src/semantic/` must go through `read_graph_file_text()` / `read_graph_page_text()` unless allowlisted in the check script.

---

## Related specs

- [`link-verification.md`](link-verification.md) — extract/verify/flag pipeline
- [`agent-ax-robustness.md`](agent-ax-robustness.md) — MCP page-title normalization (complements sandbox rejects)
- [`agent-onboarding.md`](agent-onboarding.md) — `llms.txt` §2.4 operator summary
