# [EPIC] v2.0.0 — Shadow DB & Safe-Sync Architecture

## Context

Matryca Plumber is the local data infrastructure for headless AI agents interacting with Logseq. **v2.0.0** introduces the **Shadow DB**: a daemon-owned SQLite cache (`shadow.sqlite`) for sub-50ms hierarchical reads (FTS5 + recursive CTEs), without touching Logseq's internal indices.

**RFC & architecture debate:** [Discussion #19 — Core Architecture Evolution](https://github.com/MarcoPorcellato/matryca-plumber/discussions/19)

## Safe-Sync (read/write decoupling)

| Path | Rule |
|------|------|
| **READ** | Shadow DB syncs read-only from Markdown (Classic) or Markdown Mirror (Logseq DB) |
| **WRITE (Logseq OG)** | Append to `.md` + OCC — **done in v1.9.5** → #25 |
| **WRITE (Logseq DB)** | Official CLI/API only (`qmd`) — never native DB mutation |

Full contract: [`SYSTEM_PROMPT.md`](SYSTEM_PROMPT.md) § "LLM OS" / Safe-Sync · [`docs/openspec/llm-os-instructions.md`](docs/openspec/llm-os-instructions.md)

## Delivered in v1.9.x (not part of this epic)

| Release | Deliverable |
|---------|-------------|
| v1.9.2 | `llms.txt` agent-zero-friction |
| v1.9.5 | LLM OS Soft Gate + `bootstrap_status` — tracked in milestone **v1.9.6 - Agent UX** (#21, #22 closed) |
| v1.9.5 | Safe-Sync docs + Logseq OG write path — partial #25 |

## Sub-issues (track implementation here)

| Issue | Scope |
|-------|-------|
| #17 | `GraphRepository` abstraction (Markdown + Logseq DB adapters) |
| #24 | Shadow DB read path (`shadow.sqlite`, FTS5, CTEs, background sync) |
| #25 | Safe-Sync write path (Logseq DB CLI bridge — OG path done) |
| #23 | Hardware profiler & LLM recommender (DX; independent) |

## Maintainer roadmaps (in-repo)

| Document | Scope |
|----------|-------|
| [`docs/roadmaps/ROADMAP_V2_SHADOW_DB.md`](docs/roadmaps/ROADMAP_V2_SHADOW_DB.md) | Shadow DB schema, FTS5, sync tasks — DDL in `src/shadow/schema.py` |
| [`docs/roadmaps/ROADMAP_V2_BIOLOGICAL_MEMORY.md`](docs/roadmaps/ROADMAP_V2_BIOLOGICAL_MEMORY.md) | Nacre-inspired memory graph (decay, recall, procedures) on top of Shadow DB |

## v2.0 rollout

| Track | Target |
|-------|--------|
| v2.0.0-alpha | Experimental `shadow.sqlite` + opt-in env flag |
| v2.0.0-rc | MCP read traffic routed to Shadow DB by default |
| v2.0.0-stable | Deprecate pure in-memory BM25 as default discovery path |

## Diagnostics note

There is **no** `matryca doctor` subcommand (see `llms.txt` §2.3). Shadow DB health checks will extend **preflight** / dashboard surfaces instead.
