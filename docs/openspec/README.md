# Openspec-style notes (Matryca)

Trimmed behavioral specs aligned with [MehmetGoekce/llm-wiki](https://github.com/MehmetGoekce/llm-wiki) openspec, mapped to this repository.

**Canonical checklists:** [`ROADMAP_LLM_WIKI.md`](../../ROADMAP_LLM_WIKI.md), [`ROADMAP_LLM_WIKI_PHASE_3.md`](../../ROADMAP_LLM_WIKI_PHASE_3.md) in the repo root.

| Document | Scope |
|----------|--------|
| [`ingest.md`](ingest.md) | Search → Scan → Update ingest phases (MCP + Logseq OG). |
| [`lint.md`](lint.md) | On-disk lint: block refs + wiki convention pack. |
| [`l1-l2-routing.md`](l1-l2-routing.md) | L1 memory vs L2 graph routing and MCP hints. |
| [`runtime-bootstrap.md`](runtime-bootstrap.md) | Startup directory/config provisioning (logs, L1, cache, wiki YAML). |

Implementation entry points: `src/main.py`, `src/utils/runtime_bootstrap.py`, `src/agent/mcp_server.py`, `src/config.py`, `src/graph/`, `src/rag/`.
