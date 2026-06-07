### Problem / motivation

Replace the v1.9.5 read path (`master_catalog.json` + in-memory Okapi BM25) with a relational **Shadow DB** for <50 ms latency and hierarchical queries.

### Current baseline (v1.9.5 — to be replaced)

| Component | Location |
|-----------|----------|
| JSON catalog | `.matryca_semantic_cache/master_catalog.json` — `src/graph/master_catalog.py` |
| BM25 search | `src/graph/generational_cache.py` (`get_cached_bm25_corpus`) |
| Human catalog hub | `pages/Matryca Master Index.md` (retained in v2.0) |

### Tasks

- [ ] Scaffold `shadow.sqlite` schema (pages, blocks, parent-child, block-refs)
- [ ] Async ingestion from Markdown (Classic Logseq or DB Markdown Mirror)
- [ ] FTS5 full-text index over block contents
- [ ] Recursive CTEs (`WITH RECURSIVE`) for sub-tree / thought-chain extraction
- [ ] Background sync daemon (read-only on source `.md` files)

### Dependencies

- Blocked by #17 (`GraphRepository` abstraction) for clean storage routing

### Related

Parent epic: #20
