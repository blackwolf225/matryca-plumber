# Bug Execution Plan — Contract for Composer 2.5

> Planner: The Architect. Executioner: Composer 2.5.
> Scope: 4 high-impact latent bugs found in `src/agent/`, `src/graph/`, `src/utils/`.
> Hard constraint: every change is surgical and backward compatible. The suite is at **691 green tests** and MUST stay green.
> Composer: apply the phases **in order**. After each phase run its Verification Command. Run the global gate (bottom of file) only after all 4 phases are applied.

---

## Audit summary

| Phase | File | Bug class | Risk |
|---|---|---|---|
| 1 | `src/graph/alias_index.py` | Parsing edge-case: naive comma split corrupts multi-alias index | Wrong entity resolution |
| 2 | `src/utils/json_repair.py` | Parsing edge-case: string-unaware `rfind` truncates recovered JSON | Silent LLM-payload corruption |
| 3 | `src/agent/journey_log.py` | Unhandled edge-case: bare `int()` crashes daemon state restore | Daemon cannot restart |
| 4 | `src/graph/link_verification.py` | Parsing edge-case: bullet regex ignores `*` / `+` blocks | Links/assets silently unverified |

---

### Phase 1: Alias index splits commas inside quotes and wikilinks

- **Target File:** `src/graph/alias_index.py`
- **Target Function/Class:** `_split_alias_segments`
- **Problem:** `_split_alias_segments` does `raw.split(",")`, so `alias:: [[Acme, Inc]], Acme Corp` is shattered into `[[Acme`, `Inc]]`, `Acme Corp`, poisoning `alias_to_page` and breaking entity resolution. The repo already has a quote/wikilink-aware splitter (`split_logseq_property_list_values` in `mldoc_properties.py`) used elsewhere (`append_page_alias_line`); this code path simply fails to reuse it.
- **Required Action for Composer:**
  1. Add one import line immediately **above** the existing line `from .page_path import page_title_from_path as _page_title_from_path` (currently line 14):
     `from .mldoc_properties import split_logseq_property_list_values`
  2. Replace the entire body of `_split_alias_segments` (currently lines 33-40) with the Exact Code below.
  3. Append the regression test in the second snippet to the **end** of `tests/test_alias_index.py`.
- **Exact Code (Snippet):**

```python
def _split_alias_segments(raw: str) -> list[str]:
    """Split ``alias::`` payload on commas, respecting quotes and ``[[wikilinks]]``."""
    return split_logseq_property_list_values(raw)
```

Regression test to append to `tests/test_alias_index.py` (imports `build_alias_index` and `Path` are already present in that file):

```python
def test_build_alias_index_respects_wikilink_commas(tmp_path: Path) -> None:
    pages = tmp_path / "pages"
    pages.mkdir(parents=True)
    (pages / "Acme.md").write_text(
        "type:: entity\nalias:: [[Acme, Inc]], Acme Corp\n",
        encoding="utf-8",
    )
    idx = build_alias_index(tmp_path)
    assert idx.resolve("Acme, Inc").canonical_page_title == "Acme"
    assert idx.resolve("Acme Corp").canonical_page_title == "Acme"
```

- **Verification Command:** `uv run pytest tests/test_alias_index.py -q`

---

### Phase 2: Unbalanced-JSON recovery truncates at a brace inside a string

- **Target File:** `src/utils/json_repair.py`
- **Target Function/Class:** `_recover_unbalanced_json_slice` (plus a new private helper `_last_structural_close`)
- **Problem:** When the balanced scan fails (truncated LLM output), recovery uses `collapsed.rfind(close_char)`, which is string-unaware. For `{"note": "use } here", "score": 1` it cuts at the `}` inside the string, dropping `"score": 1` and producing corrupt JSON. The fix scans for the last `}`/`]` that lies **outside** any string literal, leaving the downstream `balance_json_brackets` to append the real closer.
- **Required Action for Composer:** Replace the entire existing function `_recover_unbalanced_json_slice` (currently lines 113-129) with the Exact Code below. This **prepends** the new helper `_last_structural_close` and keeps the rest of the recovery logic identical (same `_FALLBACK_UNBALANCED_JSON_CHARS` cap and `logger.warning`).
- **Exact Code (Snippet):**

```python
def _last_structural_close(text: str, start: int, *, close_char: str) -> int:
    """Index of the last ``close_char`` outside any JSON string literal, or ``-1``."""
    in_string = False
    escape = False
    last = -1
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == close_char:
            last = index
    return last


def _recover_unbalanced_json_slice(text: str, *, open_char: str, close_char: str) -> str:
    """Salvage prefix when the model never closed braces (truncation or tail loop)."""
    collapsed = collapse_all_degenerate_llm_runs(text)
    start = collapsed.find(open_char)
    if start == -1:
        return collapsed
    close_idx = _last_structural_close(collapsed, start, close_char=close_char)
    if close_idx > start:
        return collapsed[start : close_idx + 1]
    if len(collapsed) - start > _FALLBACK_UNBALANCED_JSON_CHARS:
        logger.warning(
            "Unbalanced JSON slice capped at {} chars (no closing {})",
            _FALLBACK_UNBALANCED_JSON_CHARS,
            close_char,
        )
        return collapsed[start : start + _FALLBACK_UNBALANCED_JSON_CHARS]
    return collapsed[start:]
```

Regression test to append to `tests/test_json_repair.py`. If `loads_repaired_json` is not already in that file's imports from `src.utils.json_repair`, add it to the existing import block:

```python
def test_recover_unbalanced_preserves_keys_after_brace_in_string() -> None:
    raw = '{"note": "use } here", "score": 1'
    parsed = loads_repaired_json(raw)
    assert parsed == {"note": "use } here", "score": 1}
```

- **Verification Command:** `uv run pytest tests/test_json_repair.py -q`

---

### Phase 3: Corrupt daemon state crashes journey-ledger restore

- **Target File:** `src/agent/journey_log.py`
- **Target Function/Class:** `JourneyDayLedger.from_json` (plus a new module-level helper `_coerce_int`)
- **Problem:** `from_json` calls bare `int(payload.get(...))` on every numeric field. A hand-edited, partially written, or version-mismatched `.matryca-daemon-state.json` (e.g. `"cycles": "many"` or `"links_checked": null`) raises `ValueError`/`TypeError` inside `DaemonState.from_json`, blocking daemon restart. The fix coerces each field defensively, falling back to `0`.
- **Required Action for Composer:**
  1. Insert the `_coerce_int` helper (first snippet) immediately **after** the `journey_log_enabled` function (after current line 16, before the `@dataclass` decorating `JourneyCycleStats`).
  2. Replace the body of `JourneyDayLedger.from_json` (currently lines 103-111, the `return cls(...)` call) with the second snippet.
  3. Append the regression test (third snippet) to the end of `tests/test_journey_log.py`.
- **Exact Code (Snippet):**

Helper to insert after `journey_log_enabled`:

```python
def _coerce_int(value: object, default: int = 0) -> int:
    """Best-effort int coercion for persisted ledger fields (corrupt-state resilient)."""
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
```

Replacement `return cls(...)` inside `from_json`:

```python
        return cls(
            day=str(payload.get("day", "")),
            cycles=_coerce_int(payload.get("cycles", 0)),
            llm_files_processed=_coerce_int(payload.get("llm_files_processed", 0)),
            links_checked=_coerce_int(payload.get("links_checked", 0)),
            dead_links_flagged=_coerce_int(payload.get("dead_links_flagged", 0)),
            missing_assets_flagged=_coerce_int(payload.get("missing_assets_flagged", 0)),
            fast_track_files=_coerce_int(payload.get("fast_track_files", 0)),
        )
```

Regression test to append to `tests/test_journey_log.py` (`JourneyDayLedger` is already imported there):

```python
def test_journey_day_ledger_from_json_tolerates_corrupt_fields() -> None:
    ledger = JourneyDayLedger.from_json(
        {"day": "2026-06-10", "cycles": "many", "links_checked": None}
    )
    assert ledger.day == "2026-06-10"
    assert ledger.cycles == 0
    assert ledger.links_checked == 0
```

- **Verification Command:** `uv run pytest tests/test_journey_log.py -q`

---

### Phase 4: Link verification ignores `*` and `+` bullets

- **Target File:** `src/graph/link_verification.py`
- **Target Function/Class:** module-level constant `_BULLET_RE` (consumed by `extract_links_from_page` and `_mutate_block_hygiene_property`)
- **Problem:** `_BULLET_RE = re.compile(r"^(\s*)-\s+(.*)$")` only matches `-` bullets. The rest of `src/graph/` treats `[-*+]` as bullets (`mldoc_properties._BULLET`, `markdown_blocks`). A block written with `*` or `+` fails the match, so its URLs/assets are never extracted and can never be flagged `dead-link::` / `missing-asset::`. Widening the character class preserves both capture groups (group 1 = indent, group 2 = content), so all existing `-` behavior is unchanged.
- **Required Action for Composer:**
  1. Replace the single line at the `_BULLET_RE` definition (currently line 51) with the Exact Code below.
  2. Append the regression test (second snippet) to the end of `tests/test_link_verification.py`.
- **Exact Code (Snippet):**

```python
_BULLET_RE = re.compile(r"^(\s*)[-*+]\s+(.*)$")
```

Regression test to append to `tests/test_link_verification.py` (`Path` and `extract_links_from_page` are already imported there):

```python
def test_extract_links_from_page_handles_star_bullet(tmp_path: Path) -> None:
    root = tmp_path / "graph"
    pages = root / "pages"
    pages.mkdir(parents=True)
    page = pages / "star.md"
    page.write_text(
        "\n".join(
            [
                "* Read https://example.com/star",
                "  id:: cccccccc-cccc-cccc-cccc-cccccccccccc",
                "",
            ],
        ),
        encoding="utf-8",
    )
    content = page.read_text(encoding="utf-8")
    entries = extract_links_from_page(root, page, content)
    assert any(e.kind == "url" and e.target == "https://example.com/star" for e in entries)
```

- **Verification Command:** `uv run pytest tests/test_link_verification.py -q`

---

## Global verification gate (run once, after all 4 phases)

```bash
uv run ruff check src tests
uv run mypy src tests
uv run pytest -q
```

Success criteria: ruff clean, mypy clean, **all tests green (>= 691 + 4 new = 695)**. If any phase fails verification, fix only the code introduced by that phase and re-run — do not touch unrelated code.
