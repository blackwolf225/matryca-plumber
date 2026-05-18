---
name: Bug report
about: Report unexpected behavior or a crash
title: "[Bug] "
labels: bug
---

## Summary

<!-- Short description of what went wrong. -->

## Steps to reproduce

1.
2.
3.

## Expected behavior

<!-- What you thought should happen. -->

## Actual behavior

<!-- What happened instead (errors, logs, screenshots if useful). -->

## Environment

- **Logseq version** (Help → About):
- **Python version** (`python --version` / `uv run python --version`):
- **matryca-logseq-llm-wiki version** (commit SHA or tag):
- **OS** (e.g. macOS 14, Ubuntu 22.04, Windows 11):
- **MCP host** (e.g. Cursor, Claude Desktop, other):

## Configuration (redact secrets)

<!-- Relevant env vars or `.env` keys only — never paste `LOGSEQ_API_TOKEN` or LLM keys. -->

```text
LOGSEQ_API_URL=...
LOGSEQ_GRAPH_PATH=...
(replace values with placeholders if needed)
```

## Local checks

- [ ] I ran `make check` (or the same commands as CI: ruff, ruff format --check, mypy, pytest) before opening this issue.

## Additional context

<!-- Optional: minimal vault snippet, tool name, or link to related docs. -->
