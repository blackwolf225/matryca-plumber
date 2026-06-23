#!/usr/bin/env bash
# Maintainer-only: scaffold .local/ tooling (never published — see .gitignore).
# TRIZ separation-in-space: vendor-specific graph indexer lives under .local/, not in OSS tree.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOOLING="$ROOT/.local/tooling"
PKG="${LOCAL_GRAPH_ANALYZER_NPM_PACKAGE:-}"

mkdir -p "$TOOLING" "$ROOT/.local/agent-skills/code-graph"

if [[ -z "$PKG" ]]; then
  echo "Set LOCAL_GRAPH_ANALYZER_NPM_PACKAGE to your npm graph-analyzer package name, then re-run." >&2
  echo "Example (shell profile, not committed): export LOCAL_GRAPH_ANALYZER_NPM_PACKAGE=<your-package>" >&2
  exit 1
fi

if [[ ! -f "$TOOLING/package.json" ]]; then
  cat >"$TOOLING/package.json" <<EOF
{
  "private": true,
  "dependencies": {
    "$PKG": "^1.6.1"
  }
}
EOF
fi

echo "Installing graph analyzer CLI under .local/tooling/ ..."
npm install --prefix "$TOOLING"

# Personal git exclude (not committed) — analyzer root artifacts derived from package name.
EXCLUDE="$ROOT/.git/info/exclude"
mkdir -p "$(dirname "$EXCLUDE")"
for _pat in ".$PKG" ".${PKG}rc"; do
  if ! grep -qxF "$_pat" "$EXCLUDE" 2>/dev/null; then
    echo "$_pat" >>"$EXCLUDE"
  fi
done

CLI_BIN="$TOOLING/node_modules/.bin/$PKG"
if [[ ! -x "$CLI_BIN" ]]; then
  echo "Expected CLI at $CLI_BIN — check LOCAL_GRAPH_ANALYZER_NPM_PACKAGE." >&2
  exit 1
fi

if [[ ! -f "$ROOT/.local/env.sh" ]]; then
  cat >"$ROOT/.local/env.sh" <<EOF
# Maintainer-local (gitignored). Source before reindex-code-graph / make reindex-graph.
export LOCAL_GRAPH_ANALYZER_NPM_PACKAGE="$PKG"
export CODE_GRAPH_CLI="$CLI_BIN"
export HF_HOME="\${HF_HOME:-\$HOME/.cache/huggingface}"
EOF
  echo "Wrote .local/env.sh (gitignored)."
fi

echo "Local workspace ready. Source: . .local/env.sh"
