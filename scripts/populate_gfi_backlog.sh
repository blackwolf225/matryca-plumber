#!/usr/bin/env bash
# Populate Good First Issue backlog: Tier A labels/comments, #45 retitle, Tier B new issues.
# Requires: gh auth with repo write scope.
# Usage: bash scripts/populate_gfi_backlog.sh
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
  if ! gh label create _gfi_write_probe --repo "$REPO" --description "probe" --color "000000" 2>/dev/null; then
    echo "ERROR: GitHub token lacks write access on $REPO"
    echo "Run: gh auth refresh -h github.com -s repo"
    exit 1
  fi
  gh label delete _gfi_write_probe --repo "$REPO" --yes 2>/dev/null || true
}

tag_gfi() {
  local issue="$1"
  gh issue edit "$issue" --repo "$REPO" \
    --add-label "good first issue,help wanted"
  pause
}

comment_issue() {
  local issue="$1"
  local body="$2"
  gh issue comment "$issue" --repo "$REPO" --body "$body"
  pause
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

preflight

# ---------------------------------------------------------------------------
# Tier A — promote existing issues (#52, #44, #43)
# ---------------------------------------------------------------------------

log "Tier A: tag #52 #44 #43 as good first issue + help wanted"
for n in 52 44 43; do
  tag_gfi "$n"
done

log "Tier A: welcome comment on #52 (MmapTextView)"
comment_issue 52 "$(cat <<'EOF'
Hi! Thanks for your interest in contributing to Matryca Plumber — this is a scoped performance win in one file.

**What to fix:** In `MmapTextView.search()` and `decode_utf8()` (`src/graph/markdown_io.py`), avoid `self._mmap[:]` (full heap copy). Use `mmap.find()` for byte search where possible; for decode, respect when mmap is skipped under `MATRYCA_MMAP_MIN_BYTES`.

**Steps:**
1. Open `src/graph/markdown_io.py` and read `MmapTextView`.
2. Replace full-buffer copies in `search()` with `mmap.find()` (or equivalent) where safe.
3. Add or extend a test in `tests/test_markdown_io.py` proving search works without copying the entire file.

**Verify your fix:**
```bash
uv run pytest tests/test_markdown_io.py -q
make check
```

Comment here when you pick this up so we do not duplicate effort. No drive-by refactors needed. Welcome aboard!
EOF
)"

log "Tier A: welcome comment on #44 (daemon shutdown logging)"
comment_issue 44 "$(cat <<'EOF'
Hi! Thanks for your interest in contributing — this is a small reliability fix and a great first PR.

**What to fix:** In `_finalize_graceful_shutdown` (`src/agent/maintenance_daemon.py`), `contextlib.suppress(Exception)` around `load_master_catalog(...).save()` and `save_daemon_state(...)` hides final I/O failures during graceful teardown.

**Steps:**
1. Locate `_finalize_graceful_shutdown` and the two `suppress(Exception)` blocks.
2. Replace with explicit `try/except OSError` (or narrower types) and `logger.error(..., exc_info=True)`.
3. Do **not** change shutdown ordering or add retries — logging only.

**Verify your fix:**
```bash
uv run pytest tests/test_maintenance_daemon.py -q
make check
```

Comment here when you start. Welcome aboard!
EOF
)"

log "Tier A: welcome comment on #43 (matryca-config seed race)"
comment_issue 43 "$(cat <<'EOF'
Hi! Thanks for your interest in contributing — this is OCC hygiene on a single helper.

**What to fix:** `_ensure_config_page` in `src/agent/memory_tools.py` can race when concurrent `store_fact` calls both see a missing `matryca-config.md` and seed the page.

**Steps:**
1. Read `_ensure_config_page` and existing `page_rmw_lock` usage elsewhere.
2. Wrap the seed path with `page_rmw_lock(path)` and re-check `is_file()` / content inside the lock before `atomic_write_bytes`.
3. Add or extend a test in `tests/` covering the no-double-seed behavior (mock or thread-safe pattern).

**Verify your fix:**
```bash
uv run pytest tests/ -k memory -q
make check
```

Keep the diff surgical. Comment here when you claim it. Welcome aboard!
EOF
)"

# ---------------------------------------------------------------------------
# #45 — retitle for nanosecond OCC tests (Gaoflow in progress)
# ---------------------------------------------------------------------------

log "Retitle #45 for nanosecond OCC regression tests"
gh issue edit 45 --repo "$REPO" \
  --title "[Test] Add nanosecond OCC regression tests for link_verification"
pause

comment_issue 45 "$(cat <<'EOF'
**Scope update (maintainer):** The production fix (`file_mtime_drifted()` in `link_verification.py`) is now on `main` via the v1.9.10 nanosecond OCC wrap-up (#38). This issue is **test-only**.

Please rebase on latest `main` and replace any float-based mocks (`1.0`, `1.0 + 5e-7`) with integer `st_mtime_ns` values. See `good_first_issues_blueprints.md` § Issue #45 for the suggested tests:

- `test_flag_block_proceeds_when_mtime_unchanged_ns` — matching nanoseconds → write proceeds
- `test_flag_block_aborts_on_one_nanosecond_mtime_drift` — 1 ns drift → write aborted

**Verify:**
```bash
uv run pytest tests/test_link_verification.py -q --no-cov
make check
```

Thanks for sticking with this — the tests are the valuable part now.
EOF
)"

# ---------------------------------------------------------------------------
# Tier B — create new good-first issues
# ---------------------------------------------------------------------------

log "Tier B: create B1 (harvest mtime_ns)"
B1_URL=$(create_gfi_issue \
  "[Bug] bootstrap_harvest stores second-precision mtime in catalog entries" \
  "$(cat <<'EOF'
## Problem Description

After the v1.9.10 nanosecond OCC wrap-up (#38), `read_file_mtime()` and `file_mtime_drifted()` use `st_mtime_ns` as exact integers. `bootstrap_harvest.py` still writes `int(page_path.stat().st_mtime)` (truncated seconds) into catalog entries (~lines 207 and 274), which can disagree with OCC drift detection and `needs_refresh`.

## Proposed Solution

1. Replace `stat().st_mtime` with `stat().st_mtime_ns` when building harvest catalog entries.
2. Align with `CatalogEntry.last_mtime` / `normalize_stored_mtime_ns()` semantics in `master_catalog.py`.
3. Add or extend a regression test in `tests/test_bootstrap_yield.py`.

## Estimated Impact

Basso

## Files Involved

- `src/graph/bootstrap_harvest.py`
- `tests/test_bootstrap_yield.py`

## Verification

```bash
uv run pytest tests/test_bootstrap_yield.py tests/test_master_catalog.py -q
make check
```

---

**Good first issue** — scoped fix, existing test patterns, no maintainer-only context required.

_Related: #38 (nanosecond OCC). Closes when merged with `make check` green and CHANGELOG updated if user-visible._
EOF
)" \
  "good first issue,help wanted,v1.9.x,bug,audit-2026" \
  "$MILESTONE_V1910")
echo "Created B1: $B1_URL"

log "Tier B: create B2 (env_bool in link_verification)"
B2_URL=$(create_gfi_issue \
  "[Tech Debt] Deduplicate _env_bool in link_verification (slice of #57)" \
  "$(cat <<'EOF'
## Problem Description

`link_verification.py` defines a local `_env_bool()` helper (~line 68) that duplicates the same truthy-env parsing in `src/agent/plumber_config.py`. Drift risk when new truthy tokens are added.

## Proposed Solution

1. Remove the local `_env_bool` in `src/graph/link_verification.py`.
2. Import `_env_bool` from `plumber_config` (or the canonical module used elsewhere).
3. Optionally use `_env_int` for `MATRYCA_LINK_VERIFY_STRIKES` / `MATRYCA_LINK_VERIFY_BATCH` parsing.
4. Keep behavior identical — no default changes.

## Estimated Impact

Basso

## Files Involved

- `src/graph/link_verification.py`
- `src/agent/plumber_config.py`

## Verification

```bash
uv run pytest tests/test_link_verification.py -q
make check
```

---

**Good first issue** — scoped DRY slice of [#57](https://github.com/MarcoPorcellato/matryca-plumber/issues/57). Do not migrate other modules in the same PR.

_Closes when merged with `make check` green._
EOF
)" \
  "good first issue,help wanted,v1.9.x,tech-debt,audit-2026" \
  "$MILESTONE_V1912")
echo "Created B2: $B2_URL"

log "Tier B: create B3 (env_bool in markdown_io)"
B3_URL=$(create_gfi_issue \
  "[Tech Debt] Deduplicate env parsers in markdown_io (slice of #57)" \
  "$(cat <<'EOF'
## Problem Description

`markdown_io.py` defines local `_env_bool()` and `_env_int()` (~lines 19–33) duplicating `plumber_config.py`. Same drift risk as other env-parser copies tracked in audit #57.

## Proposed Solution

1. Remove local `_env_bool` / `_env_int` from `src/graph/markdown_io.py`.
2. Import from `plumber_config` (match import style used in sibling graph modules).
3. Preserve defaults for `MATRYCA_GRAPH_READ_MMAP` and `MATRYCA_MMAP_MIN_BYTES`.

## Estimated Impact

Basso

## Files Involved

- `src/graph/markdown_io.py`
- `src/agent/plumber_config.py`

## Verification

```bash
uv run pytest tests/test_markdown_io.py -q
make check
```

---

**Good first issue** — scoped DRY slice of [#57](https://github.com/MarcoPorcellato/matryca-plumber/issues/57). Pair with the `link_verification` slice in a separate PR to avoid conflicts.

_Closes when merged with `make check` green._
EOF
)" \
  "good first issue,help wanted,v1.9.x,tech-debt,audit-2026" \
  "$MILESTONE_V1912")
echo "Created B3: $B3_URL"

log "Tier B: create B5 (harvest semantic abort test)"
B5_URL=$(create_gfi_issue \
  "[Test] Regression: harvest skips catalog upsert when semantic index write aborts" \
  "$(cat <<'EOF'
## Problem Description

`harvest_page_into_catalog` returns early when `_append_minimal_semantic_index` fails (OCC abort), but there is no focused regression test asserting that `catalog.upsert` is **not** called in that path (`bootstrap_harvest.py` ~lines 263–269).

## Proposed Solution

1. Add a test in `tests/test_bootstrap_yield.py` that mocks `_append_minimal_semantic_index` to return `False`.
2. Assert harvest returns the expected status and that the catalog was not upserted with a stale summary.
3. Test-only PR — no production code changes unless a gap is found.

## Estimated Impact

Basso

## Files Involved

- `tests/test_bootstrap_yield.py`

## Verification

```bash
uv run pytest tests/test_bootstrap_yield.py -q
make check
```

---

**Good first issue** — test-only, documents existing OCC-safe behavior from audit #11.

_Closes when merged with `make check` green._
EOF
)" \
  "good first issue,help wanted,v1.9.x,bug,audit-2026" \
  "$MILESTONE_V1910")
echo "Created B5: $B5_URL"

log "Tier B: create B6 (semantic cache purge flock)"
B6_URL=$(create_gfi_issue \
  "[Bug] purge_expired_semantic_cache reads/deletes without json flock (slice of #42)" \
  "$(cat <<'EOF'
## Problem Description

`purge_expired_semantic_cache` in `semantic_cache_router.py` reads and deletes `*.json` cache files without `cross_process_json_flock`, while `cache_put` writes under flock. A concurrent purge vs write can race on the same file.

## Proposed Solution

1. Read `cache_put` for the existing flock pattern in `src/agent/plumber_modules/semantic_cache_router.py`.
2. Wrap per-file read/delete in `purge_expired_semantic_cache` with `cross_process_json_flock(path)`.
3. Add or extend coverage in `tests/test_semantic_cache_router.py`.

## Estimated Impact

Basso–Medio

## Files Involved

- `src/agent/plumber_modules/semantic_cache_router.py`
- `tests/test_semantic_cache_router.py`

## Verification

```bash
uv run pytest tests/test_semantic_cache_router.py -q
make check
```

---

**Good first issue** — scoped concurrency slice of [#42](https://github.com/MarcoPorcellato/matryca-plumber/issues/42). Read one existing flock call site before editing.

_Closes when merged with `make check` green and CHANGELOG updated if user-visible._
EOF
)" \
  "good first issue,help wanted,v1.9.x,bug,audit-2026" \
  "$MILESTONE_V1910")
echo "Created B6: $B6_URL"

log "Done"
cat <<EOF

Summary:
  Tier A tagged + welcomed: #52, #44, #43
  #45 retitled (test-only scope)
  New issues:
    B1 harvest mtime_ns:  $B1_URL
    B2 link_verification env: $B2_URL
    B3 markdown_io env:   $B3_URL
    B5 harvest abort test: $B5_URL
    B6 cache purge flock: $B6_URL

Update good_first_issues_blueprints.md with the new issue numbers from the URLs above.
EOF
