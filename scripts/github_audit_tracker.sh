#!/usr/bin/env bash
# =============================================================================
# github_audit_tracker.sh — Populate GitHub milestones & issues from v1.9.x audit
# =============================================================================
#
# Thin entry-point wrapper around scripts/github_audit_tracker.py.
# Follows the same patterns as scripts/github-reorg/apply.sh.
#
# Usage:
#   bash scripts/github_audit_tracker.sh              # interactive
#   bash scripts/github_audit_tracker.sh --dry-run    # preview only
#   bash scripts/github_audit_tracker.sh --yes        # non-interactive
#
# Requirements:
#   - gh CLI authenticated: gh auth status
#   - Python 3.12+
#
# Data:
#   scripts/data/v1_9_perfection_audit_issues.json
#
# DO NOT run without reviewing --dry-run output first.
# =============================================================================

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY_SCRIPT="${ROOT}/scripts/github_audit_tracker.py"
DATA_FILE="${ROOT}/scripts/data/v1_9_perfection_audit_issues.json"

die() {
  echo "ERROR: $*" >&2
  exit 1
}

# --- Preflight: dependencies -------------------------------------------------

command -v gh >/dev/null 2>&1 || die "GitHub CLI (gh) not found. Install: https://cli.github.com/"

if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON=python
else
  die "Python 3 not found."
fi

[[ -f "$PY_SCRIPT" ]] || die "Python script missing: $PY_SCRIPT"
[[ -f "$DATA_FILE" ]] || die "Audit data missing: $DATA_FILE"

# --- Delegate to Python implementation ---------------------------------------

exec "$PYTHON" "$PY_SCRIPT" "$@"
