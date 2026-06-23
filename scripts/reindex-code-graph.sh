#!/usr/bin/env bash
# Re-index this repo with hybrid BM25 + vector embeddings (maintainer-local tooling).
# Public entrypoint — delegates to .local/tooling/ (gitignored). No vendor names in OSS tree.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.local/env.sh" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.local/env.sh"
fi

LOCAL_RUNNER="$ROOT/.local/tooling/analyze-embeddings.sh"
if [[ -x "$LOCAL_RUNNER" ]]; then
  exec "$LOCAL_RUNNER" "$@"
fi

echo "Local graph indexer not provisioned." >&2
echo "  1. export LOCAL_GRAPH_ANALYZER_NPM_PACKAGE=<your-npm-package>" >&2
echo "  2. ./scripts/provision-local-workspace.sh" >&2
echo "  3. ./scripts/reindex-code-graph.sh" >&2
exit 1
