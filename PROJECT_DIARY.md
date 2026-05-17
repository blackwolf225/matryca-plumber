# Project diary and architecture decisions

This file is the **developer log** for **matryca-logseq-llm-wiki**. It records **architecture decision records (ADRs)** in a lightweight, chronological form: enough context for a future reader (or an LLM collaborator) to understand *why* the system looks the way it does, without duplicating reference material that belongs in `docs/ARCHITECTURE.md` or the source tree.

Entries are **retroactive or forward-looking** as needed. When a decision is superseded, add a new entry that references the older one rather than rewriting history.

---

## Entry template

Copy the block below when adding a new decision or milestone.

```markdown
## [YYYY-MM-DD] - Title

### Context

What problem or constraint triggered this entry? What was the situation before any change?

### Decisions Made

What was decided, rejected, or deferred? Link to PRs, commits, or paths only when it materially aids traceability.

### Next Steps

Concrete follow-ups: implementation tasks, documentation updates, experiments, or review checkpoints.
```

---

## [2026-05-17] - Foundation, DX, and The Outliner Paradigm

### Context

The project aims to connect LLM agents to **Logseq OG**—a local, **pure Markdown** knowledge graph—via MCP, without sacrificing structural fidelity. Early integration approaches risked treating Logseq pages as flat text or talking to the wrong persistence layer; block-oriented APIs also surfaced ordering bugs when child blocks were created before their parents had stable UUIDs in the graph.

### Decisions Made

- **Logseq OG (pure Markdown) over SQLite:** The system of record is the Markdown tree on disk (indented bullets, block properties, human-agent co-editing), not an opaque database export. The bridge targets Logseq’s **local HTTP JSON-RPC API** and lets Logseq own persistence to `.md` files.
- **`uv` for dependency management:** Development and CI use **Astral `uv`** (`uv sync`, `uv run`) for fast, reproducible environments; the **Makefile** exposes `install`, `lint`, `typecheck`, `test`, and `check` so contributors have a single ergonomic surface.
- **FastMCP as the MCP server framework:** `src/main.py` hosts a **FastMCP** application with lifespan-managed **`LogseqClient`** and **`MatrycaMCPServer`**, exposing tools such as **`write_logseq_outline`** over **stdio** for agent hosts that speak MCP.
- **DFS async UUID generation for hierarchical writes:** `src/agent/mcp_server.py` validates outlines with **Pydantic** (`OutlineNode`) and creates blocks **depth-first**, **awaiting** each **`append_block`** so every child is inserted under a **resolved parent UUID**. This addresses **`UNRESOLVED_PARENT_UUID`**-style technical debt from parent-child races or out-of-order creation.

### Next Steps

- ~~Implement inline spatial parsing in `src/rag/matryca_hooks.py`~~ superseded by the modular **`logseq-matryca-parser`** dependency (see diary entry **Modular Architecture and PyPI Roadmap**).
- Expand MCP tools beyond outline insertion (reads, moves, property-aware edits) as requirements stabilize.
- Keep this diary updated when transport, auth, or persistence assumptions change.

---

## [2026-05-17] - Modular Architecture and PyPI Roadmap

### Context

Spatial parsing (indentation, block tree, ``id::`` UUIDs, references) is non-trivial and would duplicate effort if reimplemented inside **matryca-logseq-llm-wiki**. A separate codebase already owns the deterministic Logseq AST work; keeping two copies would drift and complicate a future **PyPI** distribution story.

### Decisions Made

- **Single source of truth:** Parsing logic is **not** maintained in this repository. It lives in **`logseq-matryca-parser`** ([MarcoPorcellato/logseq-matryca-parser](https://github.com/MarcoPorcellato/logseq-matryca-parser)), declared in **`pyproject.toml`** as a **Git** dependency until the package is published on **PyPI**.
- **Adapter boundary:** **`src/rag/matryca_hooks.py`** exposes **`get_spatial_context(file_path)`**, which delegates to the external library (lazy import inside the function so upstream API churn is localized). This repo focuses on **orchestration** (MCP, Logseq client, RAG hooks), not parser internals.
- **Python baseline:** The parser declares **`requires-python >= 3.12`**, so this project’s interpreter floor was raised to **3.12** to stay compatible with that dependency.

### Next Steps

- When **`logseq-matryca-parser`** hits **PyPI**, replace the Git URL in **`pyproject.toml`** with a versioned PyPI spec for reproducible installs.
- Wire **`get_spatial_context`** into concrete RAG or MCP read paths as those features land.
- Keep **`docs/ARCHITECTURE.md`** in sync if the adapter’s public surface or return types change.
