# Matryca Plumber Roadmap

**North star:** [v2.0.0 — Shadow DB & Safe-Sync Architecture](https://github.com/MarcoPorcellato/matryca-plumber/milestone/3) ([Epic #20](https://github.com/MarcoPorcellato/matryca-plumber/issues/20))

Matryca Plumber is local data infrastructure for headless AI agents working with Logseq. **v2.0.0** introduces the **Shadow DB**: a daemon-owned SQLite cache (`shadow.sqlite`) for sub-50ms hierarchical reads (FTS5 + recursive CTEs), without touching Logseq's internal indices. A [`GraphRepository`](https://github.com/MarcoPorcellato/matryca-plumber/issues/17) abstraction will let Markdown (Logseq OG) and Logseq DB backends coexist, while [**Safe-Sync**](https://github.com/MarcoPorcellato/matryca-plumber/issues/25) keeps writes on the correct path — append to `.md` with OCC for OG, official CLI only for Logseq DB.

Architecture debate and RFC: [Discussion #19 — Core Architecture Evolution](https://github.com/MarcoPorcellato/matryca-plumber/discussions/19).

*Status as of v1.9.13 — issue numbers link to GitHub; scope may shift as milestones close.*

---

## Short-term (now → v1.9.12 complete)

### Community & onboarding

- README narrative refresh — hook, comparison table, architecture moved below Quick Install
- Agent surface: [`llms.txt`](llms.txt), [`.well-known/llms.txt`](.well-known/llms.txt), [`docs/openspec/agent-onboarding.md`](docs/openspec/agent-onboarding.md)
- Operator workflow in [CONTRIBUTING.md](CONTRIBUTING.md) — Discussions for RFCs, issues for trackable work
- “Test vault first” guidance in README (clone graph before pointing at production)

### Tech debt & integrity (prerequisite for v2.0)

**[v1.9.10 — Concurrency & Data Integrity](https://github.com/MarcoPorcellato/matryca-plumber/milestone/6)** ([#34](https://github.com/MarcoPorcellato/matryca-plumber/issues/34)–[#45](https://github.com/MarcoPorcellato/matryca-plumber/issues/45))

- OCC gaps on hub pages, `json_flock` parity with `page_rmw_lock`
- Atomic JSON writes for link registry and daemon state
- Catalog cache coherence under concurrent disk writers

**[v1.9.11 — Performance & I/O](https://github.com/MarcoPorcellato/matryca-plumber/milestone/7)** ([#46](https://github.com/MarcoPorcellato/matryca-plumber/issues/46)–[#56](https://github.com/MarcoPorcellato/matryca-plumber/issues/56), [#67](https://github.com/MarcoPorcellato/matryca-plumber/issues/67)–[#70](https://github.com/MarcoPorcellato/matryca-plumber/issues/70))

- Incremental AST reload instead of full-vault rescans
- Catalog and alias hot-path optimizations; checkpoint debounce
- Skip Phase 2 LLM work on daily journals; UI progress denominator fixes

**[v1.9.12 — Code Perfection & Tech Debt](https://github.com/MarcoPorcellato/matryca-plumber/milestone/8)** ([#57](https://github.com/MarcoPorcellato/matryca-plumber/issues/57)–[#64](https://github.com/MarcoPorcellato/matryca-plumber/issues/64), [#71](https://github.com/MarcoPorcellato/matryca-plumber/issues/71))

- Split `maintenance_daemon.py`; handler registry for `graph_dispatch.py`
- Centralize env parsing; eliminate `type: ignore` suppressions
- Public API on `SessionAliasRegistry`; journal page detection in graph layer

---

## Medium-term (v1.9.x → v2.0-alpha)

| Initiative | Issue | Goal |
|------------|-------|------|
| Shadow DB read path | [#24](https://github.com/MarcoPorcellato/matryca-plumber/issues/24) | `shadow.sqlite`, FTS5, CTEs, background sync from Markdown |
| GraphRepository abstraction | [#17](https://github.com/MarcoPorcellato/matryca-plumber/issues/17) | Coexistent Markdown / SQLite backends |
| Hardware Profiler & LLM Recommender | [#23](https://github.com/MarcoPorcellato/matryca-plumber/issues/23) | Sovereign UI guidance for 16 GB CPU-only laptops |
| **v2.0.0-alpha** | Epic [#20](https://github.com/MarcoPorcellato/matryca-plumber/issues/20) | Experimental `shadow.sqlite` behind opt-in env flag |

Deeper maintainer checklists (completed or in flight):

- [`docs/roadmaps/ROADMAP_LLM_WIKI.md`](docs/roadmaps/ROADMAP_LLM_WIKI.md) — LLM-Wiki baseline (done)
- [`docs/roadmaps/ROADMAP_IRONCLAD_SHIELD.md`](docs/roadmaps/ROADMAP_IRONCLAD_SHIELD.md) — resilience and safety hardening

---

## Long-term (v2.0 stable)

| Track | Target |
|-------|--------|
| **v2.0.0-rc** | MCP read traffic routed to Shadow DB by default |
| **v2.0.0-stable** | Deprecate pure in-memory BM25 as default discovery path |
| **Safe-Sync** | Logseq DB write path via official CLI only ([#25](https://github.com/MarcoPorcellato/matryca-plumber/issues/25)) |

Safe-Sync contract (read/write decoupling):

| Path | Rule |
|------|------|
| **READ** | Shadow DB syncs read-only from Markdown (Classic) or Markdown Mirror (Logseq DB) |
| **WRITE (Logseq OG)** | Append to `.md` + OCC — shipped in v1.9.5 |
| **WRITE (Logseq DB)** | Official CLI/API only — never native DB mutation |

Full spec: [`SYSTEM_PROMPT.md`](SYSTEM_PROMPT.md) § "LLM OS" / Safe-Sync · [`docs/openspec/llm-os-instructions.md`](docs/openspec/llm-os-instructions.md)

---

## Already delivered in v1.9.x

Not backlog — context for where we are today:

| Release | Deliverable |
|---------|-------------|
| v1.9.2 | `llms.txt` agent-zero-friction distribution |
| v1.9.5 | LLM OS Soft Gate, `bootstrap_status`, Safe-Sync OG write path |
| v1.9.9 | Security & Sandbox milestone |
| v1.9.13 | Enterprise Resilience (704+ tests, sandbox/RAG/automation hardening) |

---

## How to help

- **RFCs & architecture:** [GitHub Discussions](https://github.com/MarcoPorcellato/matryca-plumber/discussions)
- **Trackable work:** open [Issues](https://github.com/MarcoPorcellato/matryca-plumber/issues) — link PRs with `Fixes #N`
- **Contributing:** [CONTRIBUTING.md](CONTRIBUTING.md) · `make check` before opening a PR
