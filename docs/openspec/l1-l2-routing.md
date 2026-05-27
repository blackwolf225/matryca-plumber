# L1 / L2 routing (Matryca Plumber)

**Roadmap:** [`ROADMAP_LLM_WIKI.md`](../../ROADMAP_LLM_WIKI.md)  
**Bootstrap:** [`runtime-bootstrap.md`](runtime-bootstrap.md) (directory creation, `README.md` vs content files)

## Layers

- **L1** — `MATRYCA_L1_PATH`, `matryca-wiki.yml` `memory_path`, or `<graph-parent>/matryca-l1/*.md`. Loaded via `read_graph_data` / `target_type="memory"` (`read_l1_memory` internally). Default folder is a **sibling** of the vault (not under `pages/`) so deploy/session rules stay outside the wiki corpus (L2) and can be shared across vaults on the same machine; set `MATRYCA_L1_PATH` to `<vault>/matryca-l1` to keep L1 inside the graph root instead.
- **L2** — Logseq graph on disk under `LOGSEQ_GRAPH_PATH` and API writes.

## Files loaded into L1 context

- All `*.md` in the resolved L1 directory (non-recursive), sorted by name.
- **`README.md` is excluded** — it documents the folder for humans only.
- Starter **`session-rules.md`** is included when bootstrap creates it (replace with your real session rules).

## Hints in tool output

Successful reads may end with `<!-- matryca_routing: hint=L1_candidate|L2_default -->`.  
`write_logseq_outline` returns JSON with `routing_hint` for L2 persistence.

See `SYSTEM_PROMPT.md` and `src/agent/routing_hint.py`.
