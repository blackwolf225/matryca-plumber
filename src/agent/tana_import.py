"""Top-level orchestration for Tana workspace JSON → Logseq OG imports."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..graph.graph_path_validate import validate_logseq_graph_path
from ..graph.logseq_config import get_logseq_journal_format
from ..graph.master_catalog import load_master_catalog
from .graph_tool_helpers import graph_missing_text, graph_path_from_env
from .importers.tana.convert import convert_tana_graph
from .importers.tana.graph import TanaWorkspaceGraph
from .importers.tana.link import TanaLinkResult, link_tana_convert_result
from .importers.tana.write import TanaWriteReport, write_tana_import


@dataclass
class TanaImportResult:
    """Full pipeline outcome: load → graph → convert → link → write."""

    ok: bool
    export_path: str
    apply: bool
    error: str | None = None
    pages_planned: int = 0
    journals_planned: int = 0
    depth_splits: int = 0
    link_stats: dict[str, int] = field(default_factory=dict)
    write: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "export_path": self.export_path,
            "apply": self.apply,
            "error": self.error,
            "pages_planned": self.pages_planned,
            "journals_planned": self.journals_planned,
            "depth_splits": self.depth_splits,
            "link_stats": dict(self.link_stats),
            "write": dict(self.write),
            "warnings": list(self.warnings),
        }


def run_tana_import(
    export_path: str | Path,
    *,
    apply: bool = False,
    graph_root: str | Path | None = None,
) -> TanaImportResult:
    """Run the full Tana import pipeline (dry-run unless ``apply=True``)."""
    path = Path(export_path).expanduser()
    if not path.is_file():
        return TanaImportResult(
            ok=False,
            export_path=str(path),
            apply=apply,
            error=f"Tana export file not found: {path}",
        )

    try:
        vault = _resolve_graph_root(graph_root)
    except ValueError as exc:
        return TanaImportResult(
            ok=False,
            export_path=str(path),
            apply=apply,
            error=str(exc),
        )

    graph = TanaWorkspaceGraph.from_export(path)
    journal = get_logseq_journal_format(vault)
    convert = convert_tana_graph(
        graph,
        vault_path=vault,
        journal_page_title_format=journal.format_string,
        export_file=path.name,
    )

    catalog = load_master_catalog(vault)
    linked: TanaLinkResult = link_tana_convert_result(convert, catalog, graph=graph)
    write_report: TanaWriteReport = write_tana_import(
        linked,
        vault,
        apply=apply,
        export_file=path.name,
    )

    warnings = list(convert.warnings)
    if journal.warning:
        warnings.append(journal.warning)

    return TanaImportResult(
        ok=True,
        export_path=str(path.resolve()),
        apply=apply,
        pages_planned=len(convert.pages),
        journals_planned=len(convert.journals),
        depth_splits=convert.depth_splits,
        link_stats={
            "in_flight_resolved": linked.stats.in_flight_resolved,
            "catalog_title_resolved": linked.stats.catalog_title_resolved,
            "catalog_alias_resolved": linked.stats.catalog_alias_resolved,
            "unchanged": linked.stats.unchanged,
        },
        write=write_report.to_dict(),
        warnings=warnings,
    )


def _resolve_graph_root(graph_root: str | Path | None) -> Path:
    raw = str(graph_root).strip() if graph_root is not None else graph_path_from_env()
    if not raw:
        msg = graph_missing_text()
        raise ValueError(msg)
    return validate_logseq_graph_path(raw)


async def dispatch_tana_import(export_path: str, *, dry_run: bool = True) -> dict[str, Any]:
    """MCP entry: import a Tana export (``dry_run=True`` skips disk writes)."""
    result = run_tana_import(export_path, apply=not dry_run)
    return result.to_dict()


__all__ = [
    "TanaImportResult",
    "dispatch_tana_import",
    "run_tana_import",
]
