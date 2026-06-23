# Tana workspace JSON import (enterprise migration)

**Version:** 0.1 (draft)  
**Status:** Specified — implementation pending  
**Roadmap:** External graph migration (Tana Outliner → Logseq OG)  
**Implementation (planned):** `src/agent/tana_import.py`, `src/agent/importers/tana/`, `src/graph/logseq_config.py`  
**Architecture plan:** `.cursor/plans/tana_json_importer_5a941ef5.plan.md`  
**Related:** [`ingest.md`](ingest.md) (write pipeline + OCC), [`runtime-bootstrap.md`](runtime-bootstrap.md), [`lint.md`](lint.md), [`l1-l2-routing.md`](l1-l2-routing.md)

Matryca Plumber will **import a native Tana workspace JSON export** (flat `docs[]` graph dump) into an **active Logseq OG vault** (`LOGSEQ_GRAPH_PATH`). The importer is a **local, offline parser** — not a Tana API/MCP client. Bulk migration uses the file produced by Tana **Export workspace as JSON** ([Tana docs](https://outliner.tana.inc/docs/workspaces)); this is **not** the Tana Intermediate Format (TIF), which is import-only into Tana.

This complements **`ingest_document`**: ingestion accepts outline-shaped Markdown; Tana import accepts the proprietary flat JSON dump and performs schema translation, journal routing, depth splitting, and provenance stamping before writing via the same OCC / page-lock / post-write pipeline.

> **Terminology:** Tana **node IDs** are stored as `tana-id::` properties. Logseq **`id::` UUIDs are always freshly generated** on import — never copied from Tana.

---

## CLI / MCP surface (planned)

### CLI

```text
matryca import tana --file <export.json> [--apply] [--depth-limit N]
```

| Flag / arg | Description |
|------------|-------------|
| `--file` | Path to Tana workspace JSON export (required). |
| `--apply` | Perform writes (default: **dry-run** only). |
| `--depth-limit` | Override max outliner depth before page-split (default from `MATRYCA_TANA_DEPTH_LIMIT`, **8**). |

### MCP (v1.1)

**Signature (planned):** `import_tana(export_path: str, dry_run: bool = True, depth_limit: int | None = None) -> dict`

**Description for hosts:** *Import a Tana workspace JSON export into the Logseq graph with streaming parse, journal format compliance, depth splitting, and tana provenance metadata.*

**Response fields (typical):** `ok`, `dry_run`, `pages_created`, `journals_touched`, `depth_splits`, `links_matched`, `links_new`, `skipped_duplicates`, `peak_memory_mb`, `journal_format`, `files_touched`, `error`.

---

## Input contract: Tana raw JSON dump

| Aspect | Rule |
|--------|------|
| Source | Tana → Export workspace as JSON |
| Top-level shape | `{ formatVersion, docs: NodeDump[], … }` or wrapped `{ storeData: { docs, … } }` |
| Hierarchy | **Not nested** — parent/child via `children: string[]` ID arrays |
| Re-import into Tana | Unsupported by Tana (export is one-way) |
| Scratch files | **Never** write parse scratch under `pages/` or `journals/` (watchdog / AST cache) |

Reference reverse-engineering (algorithms only; implement fresh in Plumber):

- [supertag-cli `tana-dump.ts`](https://github.com/jcfischer/supertag-cli/blob/main/src/types/tana-dump.ts)
- [tanamigrator `scanner.py`](https://github.com/glibalien/tanamigrator/blob/main/src/core/scanner.py)

---

## Pipeline (`process_tana_import`)

| Phase | Name | Behavior |
|-------|------|----------|
| 1 | **Stream parse** | `ijson` over `docs[]`; build `id → node` and `childId → parentId` indexes |
| 2a | **Journal bootstrap** | Read `logseq/config.edn`; resolve `:journal/page-title-format` |
| 2b | **Convert** | Hybrid placement + field/tag mapping + depth limit page-split |
| 3 | **Link** | `MasterCatalog.resolve_page_title` / `resolve_alias` for existing vault pages |
| 4 | **Write** | OCC + `page_rmw_lock` + `emit_post_write_commit`; dry-run skips disk |

---

## Architectural contract 1 — `ijson` streaming (anti-OOM)

**Requirement:** Phase 1 **must** parse the export with **`ijson`** in streaming mode. **`json.load()` and `ujson.load()` are forbidden** on the Tana export file in production code paths (including tests — use the same streaming loader for parity).

**Rationale:** Tana workspace dumps can exceed hundreds of MB. Loading the full JSON DOM risks fatal OOM on 16 GB laptops.

**Implementation rules:**

1. Open export as `open(path, "rb")`.
2. Detect `storeData` wrapper via stream prefix; select ijson path `storeData.docs.item` or `docs.item`.
3. For each `docs[]` element: deserialize **one** node, validate, insert into indexes, discard raw dict.
4. Memory budget: **O(number of nodes)** for structural indexes, **not** O(file size).

**Dry-run report:** include `peak_memory_mb` when measurable.

**Dependency:** `ijson` in [`pyproject.toml`](../../pyproject.toml).

---

## Architectural contract 2 — Journal routing via `logseq/config.edn`

**Requirement:** Before routing Tana `#day` / calendar nodes, read `{LOGSEQ_GRAPH_PATH}/logseq/config.edn`, parse EDN, and extract **`:journal/page-title-format`**.

**Rationale:** Hardcoding `journals/YYYY-MM-DD.md` breaks vaults that customize journal titles (e.g. `MMM do, yyyy` → `Jun 22nd, 2026.md`). Wrong filenames are invisible to Logseq and cause calendar duplication.

**Implementation rules:**

1. `format_journal_title(iso_date: date) -> str` — semantic title Logseq expects.
2. `journal_file_path(iso_date: date) -> Path` — on-disk path under `journals/`.
3. Inline journal links `[[…]]` use the **same** formatted title as the journal file.
4. **Fallback** when `config.edn` is missing or malformed: `yyyy-MM-dd` (Logseq default) + **warning** in dry-run/apply report — do not abort the full import.
5. Path reads must use graph sandbox helpers (no traversal outside `LOGSEQ_GRAPH_PATH`).

**Module (planned):** `src/graph/logseq_config.py`, `src/agent/importers/tana/journal.py`.

**Dependency:** lightweight EDN parser (e.g. `edn_format`) if not already present.

---

## Architectural contract 3 — Depth limit + page-split (anti-freeze UI)

**Requirement:** During AST conversion, enforce a **depth limit** (default **8**, env `MATRYCA_TANA_DEPTH_LIMIT`, CLI `--depth-limit`). When a branch would exceed the limit:

1. Create (or reuse) a **dedicated page** for the node at the limit (title = node name; namespace `Tana/` when needed).
2. Replace the deep subtree in the parent with a page link: `[[Child Page Title]]` (after catalog resolution in Phase 3).
3. Move overflow content **into** the child page as root blocks (depth resets to 0).
4. Stamp **`tana-depth-split:: true`** on the bullet containing the page link.
5. Apply recursively if the split page itself receives deep branches.

**Rationale:** Tana allows unbounded indentation; Logseq Markdown outliner performance degrades severely beyond ~10 nesting levels.

**Dry-run report:** include `depth_splits` count.

---

## Architectural contract 4 — Hybrid placement

| Tana concept | Logseq destination |
|--------------|-------------------|
| Entity (`_flags % 2 == 1`, Library, page-like supertag) | Page `Tana/{Supertag}/{Name}` or `Tana/{Name}` |
| `#day` / calendar node | `journals/{user format from config.edn}.md` |
| Children of entity | Nested bullets (`- `, +2 spaces per level) on entity page |
| Supertag application | `#tag` inline and/or `type:: TagName` property |
| Field tuple | `field-name:: value` under owning bullet (keys: lowercase, `_` → `-`) |
| Done / checkbox | `TODO` / `DONE` prefix on block line |
| Tana references | `[[Title]]` after catalog resolution |

**Excluded v1:** `TRASH`, pure `SYS_*` structural nodes, mega-tuples (>50 children), Tana queries/commands/search nodes (report as `non_portable`).

---

## Architectural contract 5 — Provenance metadata (`tana-*`)

Every imported page and block carries provenance. **Tana node IDs never become Logseq `id::`.**

| Property | Scope | Description |
|----------|-------|-------------|
| `tana-id::` | Page + block | Original Tana node ID |
| `tana-export::` | Page (frontmatter) | ISO-8601 timestamp of import run |
| `tana-export-file::` | Page (frontmatter) | Source filename (basename only) |
| `tana-created::` | Block/page | Tana `props.created` when present (Unix ms) |
| `tana-modified::` | Block/page | Tana `modifiedTs` when present |
| `tana-depth-split::` | Block | `true` when this bullet is a page-split link |
| `made-by::` | New pages | `matryca plumber v…` via `stamp_plumber_authored_page` |
| `id::` | Every block | **Fresh UUID v4** — same policy as [`ingest.md`](ingest.md) |

**Idempotency (v1):** before write, scan for existing `tana-id:: <id>` in graph; if found → **skip** and report (no `--merge` in v1).

---

## Linking to existing vault content

For each proposed `[[Title]]`:

1. `MasterCatalog.resolve_page_title(title)` — case-insensitive page match.
2. Else `MasterCatalog.resolve_alias(title)` — `alias::` frontmatter match.
3. **Match** → emit `[[Canonical Title]]`; do not create duplicate page.
4. **No match** → `[[Proposed Title]]`; create page under `Tana/` namespace when needed.

In-export registry: `tana_node_id → logseq_page_title` resolves cross-references within the same dump before write ordering.

---

## Write order and concurrency

| Step | Target |
|------|--------|
| 1 | Entity pages (including depth-split pages) without external deps |
| 2 | Journal files (append, user format) |
| 3 | `Tana/Import Log` ledger + global `LOG` |
| 4 | Optional `GLOSSARY` for unmatched new terms |

Each write: `page_rmw_lock` → `OCCSnapshot.capture` → `atomic_write_bytes_if_unchanged` → `emit_post_write_commit`.

| Concern | Handling |
|---------|----------|
| OCC conflict | Abort file write; report path; same contract as `ingest_document` |
| Secret scan | `secret_violations_in_text` before any write |
| Bounds | `outline_bounds_violations` on generated outline trees |
| Git | Optional `robot(matryca): tana import …` when `MATRYCA_GIT_ROBOT_COMMIT` |
| Watchdog | No scratch files under graph root during parse |

---

## Environment

| Variable | Role |
|----------|------|
| `LOGSEQ_GRAPH_PATH` | Required — target vault |
| `MATRYCA_TANA_IMPORT_NAMESPACE` | Root namespace for imported pages (default `Tana`) |
| `MATRYCA_TANA_DEPTH_LIMIT` | Max nesting depth before page-split (default `8`) |
| `MATRYCA_GIT_ROBOT_COMMIT` | Post-write surgical commits |

Document in [`.env.example`](../../.env.example) when implementation lands.

---

## Module map (planned)

| Module | Responsibility |
|--------|----------------|
| `src/agent/importers/tana/load.py` | `ijson` streaming loader — **no** `json.load()` |
| `src/agent/importers/tana/graph.py` | Parent map, entity detection |
| `src/agent/importers/tana/tags.py` | `tagDef`, `metaNode`, tuple → supertags + fields |
| `src/agent/importers/tana/html.py` | `props.name` HTML → text + inline refs |
| `src/agent/importers/tana/journal.py` | ISO date → journal title/path |
| `src/agent/importers/tana/depth.py` | Depth limit + page-split |
| `src/agent/importers/tana/convert.py` | Tana subgraph → `OutlineNode` trees |
| `src/agent/importers/tana/link.py` | Catalog resolution + in-export ID map |
| `src/agent/importers/tana/provenance.py` | `tana-*` property builders |
| `src/graph/logseq_config.py` | `config.edn` read/cache, journal format |
| `src/agent/tana_import.py` | `process_tana_import`, CLI/MCP dispatch |
| `src/cli/__init__.py` | `import tana` subcommand |
| `src/agent/mcp_server.py` | `import_tana` tool (v1.1) |

**Tests (planned):** `tests/test_tana_import.py`, `tests/fixtures/tana/` (minimal workspace, custom `config.edn`, deep nesting, streaming large file).

---

## Operator guidance

1. **Test vault first** — clone the production graph before `--apply`.
2. **Dry-run default** — review `pages_created`, `journals_touched`, `depth_splits`, `journal_format` in JSON report.
3. **Re-import** — skipped nodes with matching `tana-id::`; use `--force` only when explicitly implemented.
4. **Not supported v1** — Tana Markdown zip, media download, Tana queries/commands, Logseq DB graph backend, semantic/embedding link merge.

---

## Risks (spec-level)

| Risk | Mitigation |
|------|------------|
| OOM on large dumps | Mandatory `ijson` streaming |
| Wrong journal filenames | `config.edn` journal format before routing |
| Logseq UI freeze | Depth limit + page-split at 8 |
| Undocumented Tana JSON schema | Permissive Pydantic `props`; fixture from anonymized real export |
| Re-import duplication | `tana-id::` dedup skip |
