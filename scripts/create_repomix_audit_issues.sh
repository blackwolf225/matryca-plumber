#!/usr/bin/env bash
# Create Repomix Audit 2026-06 GitHub issues (run once).
set -euo pipefail

REPO="MarcoPorcellato/matryca-plumber"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BODIES="$ROOT/docs/quality/issue-bodies"

create_issue() {
  gh issue create --repo "$REPO" \
    --title "$1" \
    --body-file "$2" \
    --label "$3" \
    --milestone "$4"
  sleep 2
}

create_issue \
  "[Bug] Identity config can load stale Telos from AST cache after matryca-config mtime change [Repomix Audit 2026-06]" \
  "$BODIES/140-identity-ast-stale-on-reload.md" \
  "bug,v1.9.x,audit-2026" \
  "v1.9.10 — Concurrency & Data Integrity"

create_issue \
  "[Tech Debt] RoutingHint enum for L1/L2 MCP comment hints [Repomix Audit 2026-06]" \
  "$BODIES/141-routing-hint-enum.md" \
  "tech-debt,v1.9.x,audit-2026" \
  "v1.9.12 — Code Perfection & Tech Debt"

create_issue \
  "[Tech Debt] Inject SemanticRuntimeConfig into dual-embedding indexer [Repomix Audit 2026-06]" \
  "$BODIES/142-semantic-config-injection.md" \
  "tech-debt,v1.9.x,audit-2026" \
  "v1.9.12 — Code Perfection & Tech Debt"

gh issue comment 51 --repo "$REPO" --body "$(cat <<'EOF'
## Repomix Audit 2026-06 — cross-reference

Repomix audit P1.1 proposes SQLite-backed lazy vector rows for `block_vectors.json`. This aligns with the problem statement already tracked here (full in-RAM `BlockVectorStore` + O(n) `hybrid_block_search`).

**Triage:** [`docs/quality/REPOmix_AUDIT_TRIAGE_2026-06.md`](https://github.com/MarcoPorcellato/matryca-plumber/blob/main/docs/quality/REPOmix_AUDIT_TRIAGE_2026-06.md)

**Recommendation:** treat SQLite/per-shard vectors as a **v2 Shadow DB** slice ([#24](https://github.com/MarcoPorcellato/matryca-plumber/issues/24)) rather than a parallel v1 JSON rewrite — unless a minimal v1 cap/shard lands first as a stepping stone.
EOF
)"

echo "Done."
