## Status: Implemented in v1.9.5

Closed under milestone **v1.9.6 - Agent UX**. Not a v2.0 sub-issue.

### Delivered

| Artifact | Location |
|----------|----------|
| LLM OS pointer + Soft Gate flow | `llms.txt` §6, `.well-known/llms.txt` |
| Cognitive law (3-option fallback) | `SYSTEM_PROMPT.md` § "LLM OS" |
| MCP prerequisites | `src/agent/mcp_server.py` (`read_graph_data`, `search_graph` docstrings) |
| L1 operator overlay | `matryca-l1/llm-os-rules.md` via `src/agent/l1_memory.py` |
| OpenSpec | `docs/openspec/llm-os-instructions.md` |
| Release notes | `CHANGELOG.md` [1.9.5], `docs/releases/v1.9.5-GITHUB.md` |

### Acceptance

Tier-2 agents check `bootstrap_status` and `[[Matryca Master Index]]` before blind vault search; on trigger, pause and offer Local Daemon / Blind Search / Cloud Indexing with explicit user authorization.
