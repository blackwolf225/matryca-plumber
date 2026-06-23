#!/usr/bin/env bash
# Create Expert Audit 2026-06 GitHub issues (idempotent: run once).
set -euo pipefail

REPO="MarcoPorcellato/matryca-plumber"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BODIES="$ROOT/docs/quality/issue-bodies"
API_PAUSE=2

MILESTONE_V1910="v1.9.10 — Concurrency & Data Integrity"
MILESTONE_V1911="v1.9.11 — Performance & I/O"
MILESTONE_V1912="v1.9.12 — Code Perfection & Tech Debt"
MILESTONE_V20="v2.0.0 — Shadow DB & Safe-Sync Architecture"

log() { printf '== %s ==\n' "$*"; }
pause() { sleep "$API_PAUSE"; }

preflight() {
  if ! gh auth status -h github.com &>/dev/null; then
    echo "ERROR: gh not authenticated. Run: gh auth login"
    exit 1
  fi
}

ensure_label() {
  local name="$1"
  local desc="$2"
  local color="$3"
  if ! gh label list --repo "$REPO" --search "$name" --json name -q ".[] | select(.name==\"$name\") | .name" 2>/dev/null | grep -qx "$name"; then
    gh label create "$name" --repo "$REPO" --description "$desc" --color "$color" || true
    pause
  fi
}

create_issue() {
  local title="$1"
  local body_file="$2"
  local labels="$3"
  local milestone="$4"
  gh issue create --repo "$REPO" \
    --title "$title" \
    --body-file "$body_file" \
    --label "$labels" \
    --milestone "$milestone"
  pause
}

preflight

log "Ensure audit-2026 label exists"
ensure_label "audit-2026" "Created from expert architectural audit 2026-06" "FEF2C0"

log "Creating Expert Audit issues"
I130=$(create_issue \
  "[Bug] lock_backoff downgrades processed status after successful Phase 2 write [Expert Audit 2026-06]" \
  "$BODIES/130-lock-backoff-downgrades-processed.md" \
  "bug,v1.9.x,audit-2026" \
  "$MILESTONE_V1910")
echo "I130=$I130"

I131=$(create_issue \
  "[Bug] graph_dispatch resolve/write TOCTOU — parent UUID resolved outside OCC snapshot [Expert Audit 2026-06]" \
  "$BODIES/131-graph-dispatch-resolve-write-toctou.md" \
  "bug,v1.9.x,audit-2026" \
  "$MILESTONE_V1910")
echo "I131=$I131"

I132=$(create_issue \
  "[Tech Debt] Invert graph→daemon post-write coupling via injectable port [Expert Audit 2026-06]" \
  "$BODIES/132-graph-daemon-post-write-inversion.md" \
  "tech-debt,v1.9.x,audit-2026" \
  "$MILESTONE_V1912")
echo "I132=$I132"

I133=$(create_issue \
  "[Performance] Tana import: avoid full NodeDump dict materialization [Expert Audit 2026-06]" \
  "$BODIES/133-tana-streaming-graph-builder.md" \
  "performance,v1.9.x,audit-2026" \
  "$MILESTONE_V1911")
echo "I133=$I133"

I134=$(create_issue \
  "[Performance] Generational alias/BM25 cache LRU cap across vault switches [Expert Audit 2026-06]" \
  "$BODIES/134-generational-cache-lru-cap.md" \
  "performance,v1.9.x,audit-2026" \
  "$MILESTONE_V1911")
echo "I134=$I134"

I135=$(create_issue \
  "[Bug] Phase 2 progress percent regresses when vault grows during indexing [Expert Audit 2026-06]" \
  "$BODIES/135-phase2-progress-denominator-drift.md" \
  "bug,v1.9.x,audit-2026" \
  "$MILESTONE_V1911")
echo "I135=$I135"

I136=$(create_issue \
  "[Performance] TUI dashboard: deduplicate daemon state JSON load per refresh tick [Expert Audit 2026-06]" \
  "$BODIES/136-tui-daemon-state-dedup-load.md" \
  "performance,v1.9.x,audit-2026" \
  "$MILESTONE_V1912")
echo "I136=$I136"

I137=$(create_issue \
  "[Feature] Tana re-import content-aware merge (--merge) [Expert Audit 2026-06]" \
  "$BODIES/137-tana-content-aware-reimport-v2.md" \
  "v2.0,audit-2026" \
  "$MILESTONE_V20")
echo "I137=$I137"

log "Comment on #57 (env parser DRY + invalid fallback warning)"
gh issue comment 57 --repo "$REPO" --body "$(cat <<'EOF'
## Expert Audit 2026-06 — extension (no new issue)

Triage: [`docs/quality/EXPERT_AUDIT_TRIAGE_2026-06.md`](https://github.com/MarcoPorcellato/matryca-plumber/blob/main/docs/quality/EXPERT_AUDIT_TRIAGE_2026-06.md)

**Additional slice for this umbrella:**

1. **`_safe_nonneg_int` / `_map_int` warnings** — when env or UI supplies a non-integer or negative value that is clamped/replaced with the default, emit `logger.warning` naming the key and the fallback. Operators currently get silent misconfiguration (including typo keys like `MATRYCA_PLUMBER_COMPRESION_TRIGGER_TOKENS`).

2. **Slices #90–#91** remain the first DRY wins (`link_verification`, `markdown_io`).

Related new issues from the same audit: lock_backoff downgrade (#130), graph_dispatch TOCTOU (#131), generational cache LRU (#134).
EOF
)"
pause

log "Done. Issue URLs:"
echo "$I130"
echo "$I131"
echo "$I132"
echo "$I133"
echo "$I134"
echo "$I135"
echo "$I136"
echo "$I137"
