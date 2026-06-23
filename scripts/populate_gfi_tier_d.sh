#!/usr/bin/env bash
# Tier D — post-#105 good-first issues (TUI observability slices + small tests).
# Requires: gh auth with repo write scope.
# Usage: bash scripts/populate_gfi_tier_d.sh
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
  local body="$2"
  local labels="$3"
  local milestone="$4"
  gh issue create --repo "$REPO" \
    --title "$title" \
    --body "$body" \
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

log "Tier D: create D1 (TUI scan metrics logging)"
D1=$(create_gfi_issue \
  "[Bug] TUI dashboard suppresses scan metrics and Phase-2 progress failures (slice of #102)" \
  "$(cat <<'EOF'
## Problem Description

[#102](https://github.com/MarcoPorcellato/matryca-plumber/issues/102) fixed activity-tail and `collect_snapshot_safe` state-load logging. `collect_snapshot` in `src/cli/tui_dashboard.py` still uses bare `except Exception` for:

1. `compute_scan_metrics(root, state)` (~L118–121) — failures hide with `metrics = None`.
2. `compute_phase2_progress_metrics(root, state)` (~L126–134) — failures fall back to checkpoint tallies with no log line.

Operators see stale or zeroed progress in the Rich TUI without any ops-log breadcrumb.

## Proposed Architectural Solution

Replace each broad `except Exception` with explicit `except OSError` (or narrower domain types if raised) and `loguru_logger.exception(...)` / `loguru_logger.warning(...)`. Preserve existing fallback UI values — observability only.

## Estimated Impact

Basso

## Files Involved

- `src/cli/tui_dashboard.py`
- `tests/test_tui_dashboard.py`

---

**Parent:** #102 (TUI observability) · Milestone: v1.9.12 — Code Perfection & Tech Debt

_Closes when merged with tests green (`make check`) and CHANGELOG updated per `06-auto-changelog.mdc`._
EOF
)" \
  "good first issue,help wanted,v1.9.x,bug,dx" \
  "$MILESTONE_V1912")
echo "Created D1: $D1"

log "Tier D: create D2 (TUI collect_snapshot_safe outer failure)"
D2=$(create_gfi_issue \
  "[Bug] TUI collect_snapshot_safe swallows collect_snapshot failures (slice of #102)" \
  "$(cat <<'EOF'
## Problem Description

`collect_snapshot_safe` in `src/cli/tui_dashboard.py` (~L222–234) wraps `collect_snapshot(...)` in `except Exception` and returns a generic `"Dashboard refresh failed"` snapshot **without logging**.

Any unexpected failure (import side effect, control-room helper, token logger) is invisible in `matryca_plumber_ops.log`.

## Proposed Architectural Solution

Log with `loguru_logger.exception("TUI dashboard collect_snapshot failed")` before returning the error snapshot. Keep the existing fallback `DashboardSnapshot` shape unchanged.

## Estimated Impact

Basso

## Files Involved

- `src/cli/tui_dashboard.py`
- `tests/test_tui_dashboard.py`

---

**Parent:** #102 · Milestone: v1.9.12 — Code Perfection & Tech Debt

_Closes when merged with tests green (`make check`) and CHANGELOG updated per `06-auto-changelog.mdc`._
EOF
)" \
  "good first issue,help wanted,v1.9.x,bug,dx" \
  "$MILESTONE_V1912")
echo "Created D2: $D2"

log "Tier D: create D3 (TUI _try_load_daemon_state logging)"
D3=$(create_gfi_issue \
  "[Bug] TUI _try_load_daemon_state swallows daemon state load failures (slice of #102)" \
  "$(cat <<'EOF'
## Problem Description

`_try_load_daemon_state` in `src/cli/tui_dashboard.py` (~L86–97) catches bare `except Exception` when `load_daemon_state(graph_root)` fails, then silently returns `last_good` or an empty `DaemonState()`.

Corrupt state files, flock timeouts, or permission errors produce no log breadcrumb — the TUI may show stale metrics while the daemon is healthy.

## Proposed Architectural Solution

Catch `OSError` and `BoundedJsonError` / `ValueError` explicitly (match `load_daemon_state` failure modes); log with `loguru_logger.exception` or `warning`; preserve the `last_good` fallback behavior.

## Estimated Impact

Basso

## Files Involved

- `src/cli/tui_dashboard.py`
- `tests/test_tui_dashboard.py`

---

**Parent:** #102 · Milestone: v1.9.12 — Code Perfection & Tech Debt

_Closes when merged with tests green (`make check`) and CHANGELOG updated per `06-auto-changelog.mdc`._
EOF
)" \
  "good first issue,help wanted,v1.9.x,bug,dx" \
  "$MILESTONE_V1912")
echo "Created D3: $D3"

log "Tier D: create D4 (journal settle link registry logging)"
D4=$(create_gfi_issue \
  "[Bug] Journal structural settle suppresses link registry merge failures" \
  "$(cat <<'EOF'
## Problem Description

`_settle_journal_structural_cycle_file` in `src/agent/maintenance_daemon.py` (~L2559–2561) wraps `merge_page_links_into_registry(...)` in `contextlib.suppress(OSError)`. When the link registry sidecar is unwritable during journal Phase-1 settle, the failure is silent.

Related observability pattern: [#100](https://github.com/MarcoPorcellato/matryca-plumber/pull/100), [#108](https://github.com/MarcoPorcellato/matryca-plumber/pull/108).

## Proposed Architectural Solution

Replace `suppress(OSError)` with explicit `try/except OSError` and `logger.exception(...)`. Do **not** change settle ordering or abort the journal path on registry failure — logging only.

## Estimated Impact

Basso

## Files Involved

- `src/agent/maintenance_daemon.py`
- `tests/test_maintenance_daemon.py`

---

**Milestone:** v1.9.10 — Concurrency & Data Integrity

_Closes when merged with tests green (`make check`) and CHANGELOG updated per `06-auto-changelog.mdc`._
EOF
)" \
  "good first issue,help wanted,v1.9.x,bug,core,audit-2026" \
  "$MILESTONE_V1910")
echo "Created D4: $D4"

log "Tier D: create D5 (cognitive module fault test)"
D5=$(create_gfi_issue \
  "[Test] Cognitive module LLM fault logs warning and continues pipeline" \
  "$(cat <<'EOF'
## Problem Description

`_run_cognitive_module_safe` in `src/agent/plumber_modules/__init__.py` (~L61–77) catches module runner exceptions, logs `[COGNITIVE LLM FAULT]`, and returns an empty `ModuleOutcome` so the daemon cycle continues.

There is no focused regression test proving a failing module is logged and does not abort sibling modules.

## Proposed Architectural Solution

Add a test in `tests/test_plumber_modules.py` (or nearest existing module) that:

1. Mocks a cognitive module runner to raise `RuntimeError("model timeout")`.
2. Asserts `logger.warning` (or log capture) contains `[COGNITIVE LLM FAULT]`.
3. Asserts `outcome.modules_run` records the module and the pipeline returns without re-raising.

Test-only PR — no production changes expected.

## Estimated Impact

Basso

## Files Involved

- `tests/test_plumber_modules.py` (create if missing, or extend nearest test module)

---

**Milestone:** v1.9.12 — Code Perfection & Tech Debt

_Closes when merged with tests green (`make check`) and CHANGELOG updated per `06-auto-changelog.mdc`._
EOF
)" \
  "good first issue,help wanted,v1.9.x,tech-debt,core" \
  "$MILESTONE_V1912")
echo "Created D5: $D5"

# Extract issue numbers from URLs
n1=$(echo "$D1" | grep -oE '[0-9]+$')
n2=$(echo "$D2" | grep -oE '[0-9]+$')
n3=$(echo "$D3" | grep -oE '[0-9]+$')
n4=$(echo "$D4" | grep -oE '[0-9]+$')
n5=$(echo "$D5" | grep -oE '[0-9]+$')

log "Welcome comments"
comment_issue "$n1" "$(cat <<'EOF'
Hi! Thanks for your interest in contributing — this extends the #102 TUI observability work shipped in #109.

**What to fix:** Two bare `except Exception` blocks in `collect_snapshot` (`compute_scan_metrics` and `compute_phase2_progress_metrics`) that hide failures from the ops log.

**Steps:**
1. Read `src/cli/tui_dashboard.py` — follow the #109 pattern (`OSError` + `loguru_logger.exception`).
2. Add regression tests in `tests/test_tui_dashboard.py` mocking each helper to raise.
3. Preserve existing fallback snapshot values.

**Verify:**
```bash
uv run pytest tests/test_tui_dashboard.py -q
make check
```

Comment here when you pick this up. Welcome aboard!
EOF
)"

comment_issue "$n2" "$(cat <<EOF
Hi! Small observability slice — great first PR if you already know pytest mocking.

**What to fix:** \`collect_snapshot_safe\` returns \`"Dashboard refresh failed"\` on any \`collect_snapshot\` exception without logging.

**Verify:**
\`\`\`bash
uv run pytest tests/test_tui_dashboard.py -q
make check
\`\`\`

Pair with the scan-metrics slice (issue #$n1) in a **separate PR** if both are open — avoids \`tui_dashboard.py\` conflicts.
EOF
)"

comment_issue "$n3" "$(cat <<'EOF'
Hi! Another #102 follow-up — daemon state load path in the TUI.

**What to fix:** `_try_load_daemon_state` silently falls back to `last_good` / empty state on any exception.

**Hint:** Inspect what `load_daemon_state` actually raises (`OSError`, JSON errors) and catch narrowly.

**Verify:**
```bash
uv run pytest tests/test_tui_dashboard.py -q
make check
```
EOF
)"

comment_issue "$n4" "$(cat <<'EOF'
Hi! Same pattern as @gaoflow's shutdown logging PRs (#100, #108) — replace `suppress(OSError)` with explicit logging.

**What to fix:** `merge_page_links_into_registry` failure during journal structural settle (~L2560 in `maintenance_daemon.py`).

**Verify:**
```bash
uv run pytest tests/test_maintenance_daemon.py -q
make check
```

Logging only — do not change journal settle ordering.
EOF
)"

comment_issue "$n5" "$(cat <<'EOF'
Hi! Test-only PR — documents existing fail-safe behavior in the cognitive lint pipeline.

**What to add:** Regression test for `_run_cognitive_module_safe` when a module runner raises.

**Verify:**
```bash
uv run pytest tests/test_plumber_modules.py -q
make check
```

No production code changes expected unless you find a real gap.
EOF
)"

log "Done — update good_first_issues_blueprints.md with #$n1–#$n5"
cat <<EOF

Summary (Tier D):
  D1 TUI scan/phase2 metrics: #$n1
  D2 TUI collect_snapshot_safe: #$n2
  D3 TUI _try_load_daemon_state: #$n3
  D4 Journal link registry log: #$n4
  D5 Cognitive module fault test: #$n5
EOF
