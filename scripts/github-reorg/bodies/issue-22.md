## Status: Implemented in v1.9.5

Closed under milestone **v1.9.6 - Agent UX**. Not a v2.0 sub-issue.

### Delivered

| Component | Location |
|-----------|----------|
| Phase 1 semaphore module | `src/graph/bootstrap_status.py` |
| Daemon state source | `.matryca_daemon_state.json` via `load_daemon_state()` in `maintenance_daemon.py` |
| MCP / CLI read target | `bootstrap_status` in `graph_dispatch.py`, `mcp_server.py`, `matryca --json read bootstrap_status` |
| Tests | `tests/test_bootstrap_status.py` |

### Fields exposed

`bootstrap_complete`, `bootstrap_failed`, `bootstrap_failed_reason`, `soft_gate_active`, `phase1_in_progress`, `master_index_present`, `catalog_complete`, harvest progress.

### Acceptance

Tier-2 agents query Phase 1 state deterministically without inferring bootstrap completion from index existence alone.
