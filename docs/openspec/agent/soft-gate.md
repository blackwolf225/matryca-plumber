## LLM OS — two-tier architecture

You operate in a **strictly decoupled** Matryca stack. Violating tier boundaries wastes tokens and risks graph corruption.

### Tier map

| Tier | Runtime | Responsibility | Agent rule |
|------|---------|----------------|------------|
| **Tier 1 — Gardener** | `MaintenanceDaemon` Phase 1 (`run_bootstrap_harvest`) | Scan `pages/**/*.md`, extract/build `### Matryca Semantic Index`, persist `.matryca_semantic_cache/master_catalog.json`, compile **`[[Matryca Master Index]]`** | **NEVER** run Tier-1 work. Do not bulk-summarize the vault, append semantic index blocks, or edit `master_catalog.json`. |
| **Tier 2 — Cognitive Agent** | You (MCP / `uvx matryca-plumber` CLI) | Answer user queries, surgical graph mutations, ingest | **MUST** prefer Tier-1 output via the Master Index Soft Gate below. |

**Terminology guard:** Repo **L1 memory** (`matryca-l1/*.md`) is session deploy rules — not the Gardener. Always disambiguate "L1 memory" vs "Tier-1 Gardener".

**v2.0 note (maintainers):** When Shadow DB SQLite + FTS5 ships, replace JSON-catalog references in this section with Shadow DB query paths. The compiled `[[Matryca Master Index]]` page remains the human-readable catalog; machine retrieval moves to FTS5.

### Master Index Soft Gate (Human-in-the-Loop)

Tier-2 agents **MUST** check index availability before blind vault discovery. This is a **Soft Gate** — not a hard block on all work.

**Mandatory session open sequence:**

1. **`read_graph_data` / `target_type="memory"`** — L1 deploy rules and operator constraints.
2. **`read_graph_data` / `target_type="bootstrap_status"`** — deterministic Phase 1 semaphore (`bootstrap_complete`, progress, `bootstrap_failed_reason`). Prefer this over inferring state from index existence alone.
3. **`read_graph_data` / `target_type="page"` / `query="Matryca Master Index"`** — compiled catalog hub (`pages/Matryca Master Index.md`). Each line is `[[Exact Page Title]] — one-line summary` grouped by MARPA domain.

**Soft Gate trigger — pause if any true:**

- `bootstrap_complete` is `false` or `soft_gate_active` is `true`.
- Master Index page missing or body has no indexed entries.
- Daemon Phase 1 in progress (`bootstrap_scanned < bootstrap_total`, or Sovereign UI shows "Phase 1: Cataloging Graph").
- You would otherwise guess filenames, `grep pages/`, or run blind `bm25` on the whole vault.

**On trigger — you MUST:**

1. **Halt** the current tool chain.
2. **Explain** briefly why the index is unavailable.
3. **Present these 3 options** in natural, conversational language (cost-transparent):

| Option | Name | What happens | Cost / quality |
|--------|------|--------------|----------------|
| **A** | **Local Daemon (Recommended)** | User runs `uvx matryca-plumber plumber start` with a local/free LLM. Phase 1 indexes the graph in the background at near-zero marginal cost. | Best precision. Lowest token cost. Requires daemon setup. |
| **B** | **Blind Search** | You proceed with `search_graph` / `bm25` (and targeted reads) **without** the Master Index. | Faster now. Less precise. Higher token burn on large vaults. May miss pages or misidentify titles. |
| **C** | **Cloud Indexing** | You sequentially scan vault pages and build summaries/index blocks yourself (Tier-2 impersonating Tier-1). | **High token cost.** Scales with vault size. Warn explicitly before offering. |

4. **WAIT** for the user's **explicit authorization** before executing Option B or C.
5. **Default recommendation:** Option A unless the user needs an immediate answer and accepts imprecision (B) or cost (C).

**On green gate (index ready):**

- Select exact titles from the Master Index.
- Use `structural_hops` with known seeds.
- Use `search_graph` / `bm25` only to **refine** — not as first discovery.

**Companion reads (after gate passes or user authorizes B):** `[[Matryca Graph Insights]]`; `read_graph_data` / `dashboard` for health counts.

**Internal cache rule (v1.9.4):** `.matryca_semantic_cache/master_catalog.json` is daemon-maintained. Tier-2 agents read the **compiled Master Index page** for navigation, not the JSON file directly.

### Safe-Sync — zero interference

| Path | Rule |
|------|------|
| **READ** | Only `pages/` and `journals/` Markdown under `LOGSEQ_GRAPH_PATH` via `read_graph_data`, `search_graph`, `context load`. No raw `grep`/`find` on the vault. **NEVER** read or write Logseq desktop internal stores (SQLite/KV under app data). |
| **WRITE (Logseq OG — v1.9.5)** | Only via `mutate_graph`, `refactor_blocks`, `ingest_document`, `import_tana`, `store_fact`. All commits: **OCC** (`st_mtime` check) + `page_rmw_lock`. Default `dry_run: true` on mutators and **`import_tana`**. |
| **WRITE (Logseq DB — future)** | Official Logseq CLI/API (e.g. `qmd`) only — **never** direct Logseq native DB mutation. |
| **INGEST parse scratch** | OS temp files only — **NEVER** under `pages/` (avoids watcher churn). |
| **LOCK contention** | On `PageLockUnavailableError`: skip file, do not retry tight loops, do not mark work complete. |

### Tier-2 default tool sequence

```
memory → bootstrap_status → Matryca Master Index (page) → [Soft Gate if needed] → narrow page/subtree/xray_page → dry_run mutate → apply
```

**NEVER without user authorization:** blind `search_graph` on whole vault · `grep pages/` · direct Logseq DB · bulk vault reads · impersonate Tier-1 harvest (Option C) without explicit consent.

### Soft Gate decision tree

```text
session open: memory → bootstrap_status → Master Index page
├─ green gate (bootstrap_complete && index populated)
│   └─ narrow read (page | subtree | xray_page) → dry_run mutate → apply
├─ soft_gate_active OR index missing OR Phase 1 in progress
│   ├─ HALT tool chain → explain trigger
│   ├─ offer Option A (daemon) | B (blind search) | C (cloud indexing)
│   └─ WAIT explicit user authorization before B or C
└─ PageLockUnavailableError / OCC drift
    └─ skip file · no tight retry loops · re-read on next cycle
```
