## X-Ray mode and session aliases (`[n]`)

For large pages, prefer **`read_graph_data` / `target_type="xray_page"`** with `query` = page title. The tool returns an ultra-dense outline like `[0] Parent` / `  [1] Child` (properties stripped) and writes **`{graph_root}/.matryca_xray_state.json`** mapping each `[n]` to the real Logseq block UUID.

On later **`mutate_graph`** or **`refactor_blocks`** calls (including separate CLI invocations), pass **`[n]`** directly wherever you would use a 36-character UUID:

- `write_outline` / `inject_query`: `target` = `[0]` (parent block alias) **or** `Page Title|[0]` (recommended for local LLMs)
- `edit_property` / `generate_flashcards`: `target` or `target_uuid` = `Page Title|[1]`
- Unknown alias **without** page context → `ok: false` — re-run `xray_page` on that page to refresh the map
- **v1.9.7+ safe fallback:** `Page Title|bad-uuid` on an existing page → outline appended at page bottom; response includes `warnings` — read them before continuing

Use `target_type="page"` when you need full spatial metadata (`synthetic_id`, `source_uuid`, properties). Use **`xray_page`** when you only need topology + text and minimal tokens.

---
