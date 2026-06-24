#!/usr/bin/env bash
# Tier E — ten observability / test good-first issues (#143–#152).
# Requires: gh auth with repo write scope.
# Usage: bash scripts/populate_gfi_tier_e.sh
#
# NOTE: Issues #143–#152 were created 2026-06-24. Re-running creates duplicates.
# Prefer REST (`gh api repos/.../issues --input`) when GraphQL rate limit is exhausted.
set -euo pipefail

REPO="MarcoPorcellato/matryca-plumber"
API_PAUSE=2

MILESTONE_V1910="v1.9.10 — Concurrency & Data Integrity"
MILESTONE_V1912="v1.9.12 — Code Perfection & Tech Debt"

log() { printf '== %s ==\n' "$*"; }
pause() { sleep "$API_PAUSE"; }

preflight() {
  if ! gh auth status -h github.com &>/dev/null; then
    echo "ERROR: gh not authenticated. Run: gh auth login"
    exit 1
  fi
}

create_gfi_issue() {
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

comment_issue() {
  local issue="$1"
  local body="$2"
  gh issue comment "$issue" --repo "$REPO" --body "$body"
  pause
}

preflight
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BODY_DIR="$ROOT/docs/quality/issue-bodies"

log "Tier E: E1 graph analytics catalog load logging"
E1=$(create_gfi_issue \
  "[Bug] Graph analytics suppresses master catalog load failures" \
  "$BODY_DIR/143-graph-analytics-catalog-load-log.md" \
  "good first issue,help wanted,v1.9.x,bug,dx" \
  "$MILESTONE_V1912")
echo "Created E1: $E1"

log "Tier E: E2 checkpoint bak restore copy logging"
E2=$(create_gfi_issue \
  "[Bug] Checkpoint bak restore copy failure silent" \
  "$BODY_DIR/144-checkpoint-bak-restore-copy-log.md" \
  "good first issue,help wanted,v1.9.x,bug,core" \
  "$MILESTONE_V1910")
echo "Created E2: $E2"

log "Tier E: E3 daemon state bak restore copy logging"
E3=$(create_gfi_issue \
  "[Bug] Daemon state bak restore copy failure silent" \
  "$BODY_DIR/145-daemon-state-bak-restore-copy-log.md" \
  "good first issue,help wanted,v1.9.x,bug,core" \
  "$MILESTONE_V1910")
echo "Created E3: $E3"

log "Tier E: E4 daemon state bak sidecar write logging"
E4=$(create_gfi_issue \
  "[Bug] Daemon state .bak sidecar write failure silent" \
  "$BODY_DIR/146-daemon-state-bak-write-log.md" \
  "good first issue,help wanted,v1.9.x,bug,core" \
  "$MILESTONE_V1910")
echo "Created E4: $E4"

log "Tier E: E5 journey log upsert logging"
E5=$(create_gfi_issue \
  "[Bug] Journey log upsert suppresses write failures" \
  "$BODY_DIR/147-journey-log-upsert-log.md" \
  "good first issue,help wanted,v1.9.x,bug,core" \
  "$MILESTONE_V1910")
echo "Created E5: $E5"

log "Tier E: E6 file watcher deleted link registry logging"
E6=$(create_gfi_issue \
  "[Bug] File watcher deleted-page link registry failure silent" \
  "$BODY_DIR/148-watcher-deleted-link-registry-log.md" \
  "good first issue,help wanted,v1.9.x,bug,core" \
  "$MILESTONE_V1910")
echo "Created E6: $E6"

log "Tier E: E7 phase-2 lint link registry merge logging"
E7=$(create_gfi_issue \
  "[Bug] Phase-2 lint link registry merge failure silent (slice of #128)" \
  "$BODY_DIR/149-phase2-lint-link-registry-log.md" \
  "good first issue,help wanted,v1.9.x,bug,core,audit-2026" \
  "$MILESTONE_V1910")
echo "Created E7: $E7"

log "Tier E: E8 end-of-cycle phase-2 totals refresh logging"
E8=$(create_gfi_issue \
  "[Bug] End-of-cycle Phase-2 totals refresh failure silent (slice of #137)" \
  "$BODY_DIR/150-phase2-end-cycle-totals-log.md" \
  "good first issue,help wanted,v1.9.x,bug,dx" \
  "$MILESTONE_V1912")
echo "Created E8: $E8"

log "Tier E: E9 fast-track link registry logging"
E9=$(create_gfi_issue \
  "[Bug] Fast-track link registry registration failure silent" \
  "$BODY_DIR/151-fast-track-link-registry-log.md" \
  "good first issue,help wanted,v1.9.x,bug,core" \
  "$MILESTONE_V1910")
echo "Created E9: $E9"

log "Tier E: E10 invalid env int fallback warning"
E10=$(create_gfi_issue \
  "[Bug] plumber_config warns on invalid MATRYCA_* int env fallback (slice of #57)" \
  "$BODY_DIR/152-plumber-config-env-int-warning.md" \
  "good first issue,help wanted,v1.9.x,tech-debt,dx" \
  "$MILESTONE_V1912")
echo "Created E10: $E10"

n1=$(echo "$E1" | grep -oE '[0-9]+$')
n2=$(echo "$E2" | grep -oE '[0-9]+$')
n3=$(echo "$E3" | grep -oE '[0-9]+$')
n4=$(echo "$E4" | grep -oE '[0-9]+$')
n5=$(echo "$E5" | grep -oE '[0-9]+$')
n6=$(echo "$E6" | grep -oE '[0-9]+$')
n7=$(echo "$E7" | grep -oE '[0-9]+$')
n8=$(echo "$E8" | grep -oE '[0-9]+$')
n9=$(echo "$E9" | grep -oE '[0-9]+$')
n10=$(echo "$E10" | grep -oE '[0-9]+$')

log "Welcome comments"
comment_issue "$n1" "$(cat <<'EOF'
Hi! Thanks for contributing — small observability win in the Sovereign UI metrics path.

**What to fix:** `_count_catalog_summaries` in `src/graph/graph_analytics.py` catches bare `except Exception` and returns `0` with no log line when `load_master_catalog` fails.

**Steps:**
1. Catch `OSError` and `BoundedJsonError` explicitly (see `load_master_catalog` failure modes).
2. `logger.warning` or `logger.exception` before returning `0`.
3. Add a regression test in `tests/test_graph_analytics.py`.

**Verify:**
```bash
uv run pytest tests/test_graph_analytics.py -q
make check
```
EOF
)"

comment_issue "$n2" "$(cat <<'EOF'
Hi! Same corruption-recovery pattern as daemon state — logging only.

**What to fix:** `read_daemon_checkpoint` in `src/daemon/checkpoint.py` uses `contextlib.suppress(OSError)` when copying `.bak` over the primary checkpoint after recovery.

**Verify:**
```bash
uv run pytest tests/test_daemon_checkpoint.py -q
make check
```

Do not change recovery ordering — observability only.
EOF
)"

comment_issue "$n3" "$(cat <<'EOF'
Hi! Pairs well with @gaoflow's shutdown logging work (#100, #108).

**What to fix:** `load_daemon_state` in `src/agent/maintenance_daemon.py` (~L794) silently suppresses `shutil.copy2(bak, primary)` failures during metadata corruption recovery.

**Verify:**
```bash
uv run pytest tests/test_maintenance_daemon.py -q
make check
```
EOF
)"

comment_issue "$n4" "$(cat <<'EOF'
Hi! Backup sidecar writes should leave a breadcrumb when they fail.

**What to fix:** `save_daemon_state` (~L831) wraps `shutil.copy2(path, bak_path)` in `suppress(OSError)`.

**Verify:**
```bash
uv run pytest tests/test_maintenance_daemon.py -q
make check
```

Primary atomic write must still succeed even when `.bak` copy fails.
EOF
)"

comment_issue "$n5" "$(cat <<'EOF'
Hi! Journey Log is operator-visible — silent write failures are hard to debug.

**What to fix:** `_finalize_link_and_journey_pass` (~L2884) wraps `upsert_journey_log(...)` in `suppress(OSError)`.

**Verify:**
```bash
uv run pytest tests/test_maintenance_daemon.py -q
make check
```

Preserve non-blocking journey pass — log only.
EOF
)"

comment_issue "$n6" "$(cat <<'EOF'
Hi! File-watcher path for deleted pages — link registry should log failures like other registry merges.

**What to fix:** `_on_watchdog_change` (~L2118) suppresses `register_page_links_from_path` on `deleted` events.

**Verify:**
```bash
uv run pytest tests/test_maintenance_daemon.py tests/test_file_watcher.py -q
make check
```
EOF
)"

comment_issue "$n7" "$(cat <<'EOF'
Hi! Slice of #128 — same `merge_page_links_into_registry` pattern during Phase-2 cognitive lint.

**What to fix:** `run_cycle` Phase-2 path (~L2637) uses `suppress(OSError)` around registry merge before cognitive lint.

**Verify:**
```bash
uv run pytest tests/test_maintenance_daemon.py -q
make check
```

Pick **either** #128 or this issue per PR to avoid `maintenance_daemon.py` conflicts.
EOF
)"

comment_issue "$n8" "$(cat <<'EOF'
Hi! Slice of #137 — cycle **start** already logs `refresh_phase2_cognitive_totals` failures; cycle **end** (~L3044) still suppresses them.

**What to fix:** Replace `suppress(OSError)` with explicit `try/except OSError` + `logger.warning`.

**Verify:**
```bash
uv run pytest tests/test_maintenance_daemon.py tests/test_tui_dashboard.py -q
make check
```
EOF
)"

comment_issue "$n9" "$(cat <<'EOF'
Hi! Fast-track skippable files still register links when verification is enabled — failures should not be silent.

**What to fix:** `_try_fast_track_cycle_file` path in `run_cycle` (~L2963) suppresses `register_page_links_from_path`.

**Verify:**
```bash
uv run pytest tests/test_maintenance_daemon.py -q
make check
```
EOF
)"

comment_issue "$n10" "$(cat <<'EOF'
Hi! Config hygiene slice of #57 — great if you prefer small `plumber_config.py` changes over daemon work.

**What to fix:** `_env_int` in `src/agent/plumber_config.py` returns the default on `ValueError` with no warning. Log once per key at `logger.warning` when the env value is non-empty but not parseable.

**Verify:**
```bash
uv run pytest tests/test_plumber_config.py -q
make check
```

Match the style planned for `_env_bool` in #90/#91.
EOF
)"

log "Done — update good_first_issues_blueprints.md with #$n1–#$n10"
cat <<EOF

Summary (Tier E):
  E1 graph analytics catalog: #$n1
  E2 checkpoint bak restore: #$n2
  E3 daemon state bak restore: #$n3
  E4 daemon state bak write: #$n4
  E5 journey log upsert: #$n5
  E6 watcher deleted registry: #$n6
  E7 phase-2 lint registry: #$n7
  E8 end-of-cycle phase-2 totals: #$n8
  E9 fast-track registry: #$n9
  E10 env int warning: #$n10
EOF
