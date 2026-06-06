# Agent onboarding (`llms.txt`) — v1.9.5

**Milestone:** v1.9.2 — Agent-zero-friction distribution · v1.9.5 — LLM OS / `bootstrap_status`  
**Artifacts:** [`llms.txt`](../../llms.txt) (repo root), [`.well-known/llms.txt`](../../.well-known/llms.txt) (canonical URL path)  
**Companion spec:** [`agent-dx.md`](agent-dx.md) (CLI `--json`, `context load`, Journey Log — cumulative daily journal bullet)

External LLM hosts (Cursor, Claude Code, Windsurf, Hermes, custom agents) must reach Matryca Plumber through a **versioned PyPI wheel**, not a cloned dev tree. The `llms.txt` files encode that contract: imperative commands, verified flags, and explicit anti-patterns.

---

## Discovery paths

| Path | Audience |
|------|----------|
| `https://github.com/MarcoPorcellato/matryca-plumber/blob/main/.well-known/llms.txt` | Tools that resolve `.well-known/llms.txt` on the repository or published site |
| `llms.txt` at repo root | README agent hook, raw GitHub links, local checkouts |
| [`README.md`](../../README.md) agent callout | Human operators redirecting assistants to PyPI |

Both files must stay **byte-identical**; edit one and mirror the other in the same change.

---

## Execution contract (non-negotiable)

1. **`LOGSEQ_GRAPH_PATH`** — Absolute path to the Logseq OG vault root (`pages/`, usually `journals/`). There is **no** `--graph` CLI flag in the v1.9 line.
2. **`uvx matryca-plumber …`** — Default entry for agents. Resolves the latest compatible wheel from PyPI without polluting the user environment.
3. **`--json` before subcommand** — Machine-readable stdout; secrets redacted in-place (`redact_secrets_in_text`).
4. **No raw Markdown scraping** — Use `read`, `search`, `context load`, or MCP tools on the shared `graph_dispatch` plane.

### Anti-patterns (documented in `llms.txt`)

| Do not | Do instead |
|--------|------------|
| `git clone` + `pip install -e .` to “use” the tool | `uvx matryca-plumber` |
| `grep` / `find` on `pages/` | `uvx matryca-plumber --json read page "…"` |
| Invent `doctor`, `--graph`, `mcp --port 8080` | Commands listed in section 2 of `llms.txt` |

---

## MCP stdio (optional)

FastMCP runs over **stdio**, not HTTP. Requires `MATRYCA_MCP_ENABLED=true` and a trusted host process. See [`SECURITY.md`](../../SECURITY.md) for the trust boundary.

Host pattern (Cursor / Claude Desktop):

```json
{
  "mcpServers": {
    "matryca-logseq": {
      "command": "uvx",
      "args": ["matryca-plumber"],
      "env": {
        "LOGSEQ_GRAPH_PATH": "/absolute/path/to/vault",
        "MATRYCA_MCP_ENABLED": "true"
      }
    }
  }
}
```

---

## LLM OS contract (Tier-2 agents)

Section 6 of `llms.txt` points to the full cognitive law in [`SYSTEM_PROMPT.md`](../../SYSTEM_PROMPT.md) § "LLM OS":

- Two-tier Gardener vs Cognitive Agent awareness
- Master Index **Soft Gate** (Local Daemon / Blind Search / Cloud Indexing)
- `read_graph_data` / `bootstrap_status` semaphore before blind search

Spec: [`llm-os-instructions.md`](llm-os-instructions.md).

---

## Maintainer checklist

When adding or renaming CLI subcommands:

1. Run the command locally with `LOGSEQ_GRAPH_PATH` set.
2. Update **`llms.txt`** and **`.well-known/llms.txt`** in the same PR.
3. Cross-check [`agent-dx.md`](agent-dx.md), [`SYSTEM_PROMPT.md`](../../SYSTEM_PROMPT.md), and [`llm-os-instructions.md`](llm-os-instructions.md) if MCP discriminators or agent contracts change.
4. Ship a **patch release** so `uvx` consumers pick up accurate instructions on PyPI.

When Shadow DB SQLite + FTS5 ships (v2.0), follow the migration trigger in [`llm-os-instructions.md`](llm-os-instructions.md).

---

## Related reading

- [`llm-os-instructions.md`](llm-os-instructions.md) — two-tier architecture, Soft Gate, `bootstrap_status`
- [`agent-dx.md`](agent-dx.md) — JSON envelope, `context load`, `read subtree`, Journey Log
- [`l1-l2-routing.md`](l1-l2-routing.md) — L1 memory vs L2 graph for agents
- [`ARCHITECTURE.md`](../ARCHITECTURE.md) — three-surface runtime and distribution
- [`RELEASE_PROCESS.md`](../RELEASE_PROCESS.md) — tagging and PyPI publish via CI
