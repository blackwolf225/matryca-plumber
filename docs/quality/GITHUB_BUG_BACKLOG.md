# GitHub bug backlog — Expert Audit 2026-06 slice

Authoritative triage matrix: [`EXPERT_AUDIT_TRIAGE_2026-06.md`](EXPERT_AUDIT_TRIAGE_2026-06.md).

## Open — Expert Audit 2026-06

| Issue | Priority | Area |
|-------|----------|------|
| [#132](https://github.com/MarcoPorcellato/matryca-plumber/issues/132) | P1 | `lock_backoff` downgrades `processed` |
| [#133](https://github.com/MarcoPorcellato/matryca-plumber/issues/133) | P1 | `graph_dispatch` resolve/write TOCTOU |
| [#134](https://github.com/MarcoPorcellato/matryca-plumber/issues/134) | P1 | graph→daemon post-write inversion |
| [#135](https://github.com/MarcoPorcellato/matryca-plumber/issues/135) | P2 | Tana streaming graph builder |
| [#136](https://github.com/MarcoPorcellato/matryca-plumber/issues/136) | P2 | Generational cache LRU |
| [#137](https://github.com/MarcoPorcellato/matryca-plumber/issues/137) | P2 | Phase 2 progress regression |
| [#138](https://github.com/MarcoPorcellato/matryca-plumber/issues/138) | P2 | TUI daemon state dedup load |
| [#139](https://github.com/MarcoPorcellato/matryca-plumber/issues/139) | v2 | Tana content-aware re-import |

## Open — Repomix Audit 2026-06

| Issue | Priority | Area |
|-------|----------|------|
| [#140](https://github.com/MarcoPorcellato/matryca-plumber/issues/140) | P2 | Identity AST stale on mtime reload |
| [#141](https://github.com/MarcoPorcellato/matryca-plumber/issues/141) | P3 | `RoutingHint` enum (good-first) |
| [#142](https://github.com/MarcoPorcellato/matryca-plumber/issues/142) | P3 | `SemanticRuntimeConfig` injection |

Triage: [`REPOmix_AUDIT_TRIAGE_2026-06.md`](REPOmix_AUDIT_TRIAGE_2026-06.md)

## Related existing issues

- [#57](https://github.com/MarcoPorcellato/matryca-plumber/issues/57), [#90](https://github.com/MarcoPorcellato/matryca-plumber/issues/90)–[#91](https://github.com/MarcoPorcellato/matryca-plumber/issues/91), [#142](https://github.com/MarcoPorcellato/matryca-plumber/issues/142) — env / semantic config centralization
- [#51](https://github.com/MarcoPorcellato/matryca-plumber/issues/51) — `block_vectors.json` in-RAM + hybrid search O(n) (Repomix P1.1)
- [#70](https://github.com/MarcoPorcellato/matryca-plumber/issues/70) — Phase 2 journals excluded (closed)
- [#85](https://github.com/MarcoPorcellato/matryca-plumber/issues/85) — BootstrapHarvestStatus dedup
- [#102](https://github.com/MarcoPorcellato/matryca-plumber/issues/102), [#125](https://github.com/MarcoPorcellato/matryca-plumber/issues/125)–[#127](https://github.com/MarcoPorcellato/matryca-plumber/issues/127) — TUI observability (distinct from #138 performance)
