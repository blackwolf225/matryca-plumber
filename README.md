# Matryca Plumber

**Developed by [Marco Porcellato](https://github.com/MarcoPorcellato) · [Matryca.ai](https://matryca.ai)** — open-source local-first maintenance daemon for Logseq OG. The product name is **Matryca Plumber** (not “Matryca” alone). See [`docs/BRANDING.md`](docs/BRANDING.md).

> **v1.5 — Ironclad Release.** Agentic Knowledge Management for Logseq OG. An **enterprise-grade, local-first background AI daemon** with a real-time **Sovereign UI** control room, a **typed CLI**, and **direct Logseq Markdown AST** mutation (no Logseq HTTP API, no auxiliary database). The default experience is **autonomous**: the daemon and Python workers poll your graph, run structured local-LLM passes, and commit indexes and lint artifacts while you work or sleep. An **optional FastMCP stdio sidecar** exposes the same headless mutation plane to external clients (for example Claude Desktop) — same `graph_dispatch` contract, not a separate data path. Heavily inspired by [Andrej Karpathy's LLM-Wiki vision](https://karpathy.ai/blog). **100% native Logseq AST parity**, optimistic concurrency safety, versioned AI authorship stamping.

[![CI](https://github.com/MarcoPorcellato/matryca-plumber/actions/workflows/ci.yml/badge.svg)](https://github.com/MarcoPorcellato/matryca-plumber/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-453%20passing-brightgreen)](https://github.com/MarcoPorcellato/matryca-plumber/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)

![Matryca Plumber — Agentic Knowledge Management for Logseq OG](images/matryca-plumber-1-5-10-demo.gif)

Matryca Plumber is a **100% headless, sandboxed** **standalone daemon + CLI** that turns your local Logseq graph into a high token-density agentic workspace — **no network APIs and no Logseq desktop JSON-RPC**. It treats your vault as a **tree of blocks**, not a flat document store. Logseq OG remains optional: humans and the daemon co-edit the **same** `.md` trees on disk.

**Matryca Plumber** is not a one-shot script — it is an **enterprise-grade, local-first background AI daemon for Logseq**. It polls your graph on a duty cycle, calls a local LLM (LM Studio or Ollama), appends semantic indexes, runs optional cognitive lint modules, and logs every token transaction — **while you edit the same `.md` files in Logseq or leave the vault idle**. Optional **MCP-attached** sessions reuse the identical mutation plane for interactive queries; they are **not** required for background operation. Every write path mirrors Logseq's on-disk AST contract: page frontmatter at line 0, block properties contiguous to their parent bullet, namespace filenames encoded exactly like Logseq's Clojure Datalog layer, and **optimistic concurrency control** that aborts stale writes when you type during inference.

**Matryca Plumber** turns your local graph into a high token-density agentic workspace by continuously polling your notes, running local LLMs (like LM Studio or Ollama), appending semantic indexes, and healing broken links—all completely offline, while you work or sleep.

**Zero Cloud. Zero Data Leaks. 100% Native Logseq AST.**

---

## ⚠️ Important: Clone Your Graph First

Matryca Plumber edits your local `.md` files directly. While it features safe Optimistic Concurrency Control (OCC) to prevent data loss, **we strongly recommend testing it on a clone of your graph first**. This allows you to see the AI in action and explore its capabilities without affecting your primary notes.

**How to safely clone your graph (crucial if you use Logseq Sync):**
1. Make a copy of your entire Logseq graph folder on your computer (e.g., duplicate your `MyGraph` folder and rename it to `MyGraph_Test`).
2. Open Logseq, click on your graph name in the top left, and select **Add new graph**.
3. Choose the new `MyGraph_Test` directory.
4. **If you use Logseq Sync:** Do *not* enable Sync on this test graph. This ensures the AI's test edits remain strictly local and do not propagate to your other devices.
5. Alternatively, for a minimal test graph:
  a. Create an empty folder and add it as a new graph in Logseq.
  b. Close Logseq; copy only pages/, journals/, assets/ from production.
  c. Reopen and Re-index.
6. Point Matryca Plumber's `.env` configuration (`LOGSEQ_GRAPH_PATH`) to this test folder.

Once you are comfortable with how Matryca Plumber behaves and have tuned the safety tiers, you can point it to your main graph.

---

## 🚀 Quick Install & Getting Started

The fastest way to get started is using [uv](https://docs.astral.sh/uv/), the blazing-fast Python package manager.

### 1. Try it instantly (Zero-install)
Run the CLI directly without polluting your system. This **only opens the Sovereign UI** at [http://127.0.0.1:8500](http://127.0.0.1:8500) — it does **not** start graph maintenance until you complete the pre-flight checklist and click **Start Engine** (or run `matryca plumber start` separately).
```bash
uvx --from matryca-plumber matryca-plumber status
```
(`matryca-plumber status` is shorthand for `matryca plumber status`.)

### 2. Global Installation (Recommended)
Install the binary to use the `matryca` command anywhere:
```bash
uv tool install matryca-plumber
```

### 3. Open the control room (recommended first step)
```bash
matryca plumber status
# same as: matryca-plumber status
```
The browser opens the **Sovereign UI**. On **every** fresh visit, a **Pre-flight checklist** modal appears first (even if you already ran `matryca plumber start` in a terminal). Dismiss it with **Continue to dashboard** once the live checks are green, then click **Start Engine** in the header to launch the maintenance daemon from the UI.

**Optional — headless daemon before opening the UI:**
```bash
matryca plumber start    # background worker only; no browser
matryca plumber status   # UI still shows pre-flight; engine may already show IDLE/RUNNING
```

### 4. Set it and forget it (Background Service)
Install it as a LaunchAgent/systemd service so it wakes up with your OS:
```bash
matryca service install
```

---

## 🧠 What does it actually do?

Unlike generic scripts, Matryca Plumber is a continuous background engine. When paired with a local LLM (**Gemma 4-E4b Instruct** via LM Studio or Ollama), it provides:

- **Semantic Indexing**: Automatically generates summaries, suggested tags, and cross-references for your pages.
- **Dangling Link Healing**: Finds broken `[[WikiLinks]]` and creates isolated seed pages for them.
- **Entity Consolidation**: Suggests `alias::` properties for overlapping concepts.
- **Auto-Split Dense Blocks**: Extracts oversized subtrees into new pages to keep your graph fast and readable.
- **Claude Desktop Integration (FastMCP)**: Use Claude to query and mutate your Logseq graph natively. Set `MATRYCA_MCP_ENABLED=true` in `.env` (stdio MCP is off by default).

---

## 🖥️ The Sovereign UI

Matryca Plumber is 100% headless, but it ships with a **Sovereign UI Cockpit** (`matryca plumber status` or `uvx … matryca-plumber status`). 
It's a local React dashboard running on `http://127.0.0.1:8500` that provides:
- **Pre-flight checklist** (modal on each UI open): operator guidance plus automated readiness checks before **Start Engine** is enabled.
- **Live Graph Telemetry**: See exactly what the AI is indexing in real-time.
- **Dynamic Impact**: Mathematically separates *Organic Human Mind* (your notes) from *Agent Cognition* (AI enhancements).
- **Zero-Trust Security**: Every REST call requires a Bearer token (`X-Matryca-Token`). Session bootstrap is loopback-only; split rate limits for authenticated vs anonymous API traffic.
- **Trust & Safety Drawer**: Visually toggle what the AI is allowed to edit (Safe Mode, Augmented Mode, Surgeon Mode).

See [`SECURITY.md`](SECURITY.md) for the full operator hardening matrix (`MATRYCA_MCP_ENABLED`, graph path allowlist, shared LLM SSRF policy, log redaction).

### Pre-flight checklist (what you see in the app)

Matryca Plumber provisions missing runtime files automatically where possible (repo `.env` from `.env.example`, `matryca-l1/`, cache dirs, `matryca-wiki.yml`). The modal still walks you through setup so nothing surprises you on first run. It is developed by **Marco Porcellato** at **[Matryca.ai](https://matryca.ai)** — the same attribution shown in the Sovereign UI pre-flight wizard.

**Operator steps (same text as the UI wizard):**

1. **Control room connection** — If you can read this dashboard, the local API on port `8500` is up. Keep the window open while the engine runs.

2. **Logseq graph (test vault first)** — Point `LOGSEQ_GRAPH_PATH` at the **root** of a Logseq OG vault (the folder that contains `pages/`). Use a **clone** for your first run; do not enable Logseq Sync on test graphs. In the UI: **Settings** (gear) → **Logseq Graph Path** → absolute path → Save.

3. **Local LLM** — Start an OpenAI-compatible server (LM Studio, Ollama, etc.). In Settings set the base URL (e.g. `http://localhost:1234/v1`) and the **exact** model id, then **Refresh models** to confirm discovery.

   **Matryca Plumber** (by Marco Porcellato · Matryca.ai) is built for **offline, CPU-only** use on a typical **16 GB RAM** machine — no cloud subscription or discrete GPU required. The **recommended and tested** model is **Gemma 4-E4b Instruct** — set the exact id `gemma-4-e4b-it` in Settings, then **Refresh models**. For responsive CPU inference (about **15–30 tokens/second**), prefer **GGUF** weights at **`Q4_K_M`** or **`Q5_K_M`**. We are actively testing additional open models to improve CPU-only, 16 GB setups; Gemma 4-E4b Instruct is our current default. Avoid large **MoE** models (e.g. Llama 4 Scout): full weights still require 60GB+ RAM.

4. **First-run expectations** — **Phase 1** catalogs the entire graph (can take a long time on large vaults). **Phase 2** processes roughly one LLM-heavy page per poll interval by default.

**Live checks** (re-run anytime with **Re-run checks**):

| Check | What it validates |
|-------|-------------------|
| Environment file | Repository `.env` exists (created from `.env.example` on first boot when possible). |
| Logseq graph path | `LOGSEQ_GRAPH_PATH` is set and points at a valid vault root. |
| L1 session memory | Sibling `matryca-l1/` (or configured `MATRYCA_L1_PATH` / wiki `memory_path`) is ready. |
| Local LLM endpoint | `LLM_BASE_URL` passes SSRF policy and `GET /v1/models` responds; warns if the configured model id is not listed. |

**Start Engine** stays disabled until every live check is green. If you started the daemon earlier with `matryca plumber start`, the UI may already show **IDLE** or **RUNNING** and **Start Engine** may be disabled — the pre-flight modal still opens so you can review settings; use **Pre-flight** in the header to reopen it later.

---

## ✨ Key Features & Differentiators

* 🤖 **100% Local-First & Headless:** No Logseq HTTP API required. It edits the `.md` files directly using atomic file I/O.
* 📐 **Exact Logseq AST Compliance:** True line-0 page frontmatter, block properties at +2 indent, and exact namespace encoding. Other tools break your graph; Matryca Plumber keeps it pristine.
* 🔐 **Optimistic Concurrency Control:** It checks `st_mtime` before any AI inference. If you typed in Logseq while the AI was "thinking", Matryca Plumber aborts its write. **No silent data loss.**
* 🪟 **Windows, macOS & Linux Support:** Runs safely in the background everywhere using a robust cross-platform lock (`.matryca_plumber_daemon.lock`).
* ⚡ **Context Acceleration Shield:** Obliterates LLM prefill latency on 5,000+ block pages by using hierarchical summaries instead of raw megabyte-class text.

---

## 🛡️ Trust & Safety Risk Tiers

You are in control. Nothing mutates your prose unless you explicitly enable it in the UI.

| Mode | Risk | What it allows |
|------|------|----------------|
| 🟢 **Safe Mode** | Read-only | Semantic routing cache, entity consolidation (`alias::`), property hygiene — **never edits your bullet text**. |
| 🟠 **Augmented Mode** | Side-blocks | **Heal Dangling Links**, **Backpropagate Links** (appends foldable context sections) — your original bullets stay intact. |
| 🔴 **Surgeon Mode** | Inline edits | **Inline Semantic Corrections** (wraps concepts in `[[WikiLinks]]`), **Auto-Split Dense Blocks** — **strictly opt-in**. |

---

## ⚙️ Configuration Quickstart

Copy `.env.example` to `.env`. The only **required** variable is your graph path:

```env
LOGSEQ_GRAPH_PATH=/absolute/path/to/your/Logseq/graph
MATRYCA_LM_BASE_URL=http://localhost:1234/v1   # LM Studio or Ollama endpoint
MATRYCA_LM_MODEL=gemma-4-e4b-it                # Gemma 4-E4b Instruct — tested default

# Optional: Claude Desktop / Cursor MCP (off by default)
MATRYCA_MCP_ENABLED=true
```

On first start (daemon, CLI, MCP, or UI), Matryca Plumber **automatically creates** anything missing for a healthy runtime:

- **`logs/`** (or paths from `MATRYCA_PLUMBER_LOG_PATH` / `MATRYCA_LOGURU_LOG_PATH`)
- **`<parent-of-your-vault>/matryca-l1/`** — session rules beside the vault (not inside `pages/`); optional override via `MATRYCA_L1_PATH`
- **`<vault>/.matryca_semantic_cache/`**, **`templates/`**, and **`matryca-wiki.yml`** (from `matryca-wiki.example.yml` when absent)

See [`docs/openspec/runtime-bootstrap.md`](docs/openspec/runtime-bootstrap.md) for rationale (L1 vs L2, idempotency, and what is intentionally *not* auto-created).

*(See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for advanced thermal pacing, context compression, and deep linter settings. Copy the full template from `.env.example` — it documents UI auth, rate limits, graph allowlists, and log redaction.)*

---

## 🧑‍💻 Developer Setup

Want to contribute or run from source?

```bash
git clone [https://github.com/MarcoPorcellato/matryca-plumber.git](https://github.com/MarcoPorcellato/matryca-plumber.git)
cd matryca-plumber
make install

# Build the React frontend
cd frontend && npm install && npm run build && cd ..

# Run tests (453 passing, 0 Mypy strict issues)
make check
```

---

## 📚 Documentation Map

| Document | Description |
|----------|-------------|
| [`SYSTEM_PROMPT.md`](SYSTEM_PROMPT.md) | Agent discipline, `made-by::` authorship, OCC rules. |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Data planes, Plumber lifecycle, RMW locking rationale. |
| [`docs/BRANDING.md`](docs/BRANDING.md) | Product name (**Matryca Plumber**), Matryca.ai attribution, writing rules. |
| [`docs/openspec/runtime-bootstrap.md`](docs/openspec/runtime-bootstrap.md) | Startup provisioning: logs, L1, cache, wiki YAML. |
| [`docs/openspec/l1-l2-routing.md`](docs/openspec/l1-l2-routing.md) | L1 memory vs L2 graph routing for agents. |
| [`docs/PROJECT_DIARY.md`](docs/PROJECT_DIARY.md) | Maintainer log, phase history, crushed bottlenecks. |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Setup, `uv` commands, `make check` standards. |
| [`SECURITY.md`](SECURITY.md) | Vulnerability reporting and `.env` hardening controls. |

## License
Apache-2.0 — see [LICENSE](LICENSE).

![Matryca Plumber Cover](images/20260519-Logseq-Matryca-LLM-Wiki-copertina-github.jpg)
