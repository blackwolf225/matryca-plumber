"""Apply linked Tana import plans to the Logseq graph with idempotent OCC writes."""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ....graph.alias_index import is_scannable_graph_markdown, iter_scannable_pages_markdown
from ....graph.markdown_blocks import (
    OCCSnapshot,
    atomic_write_bytes,
    atomic_write_bytes_if_unchanged,
    canonical_line_suffix,
    graph_safe_page_path,
    strip_line_endings,
)
from ....graph.page_properties import inject_page_properties, stamp_plumber_authored_page
from ....graph.page_write_lock import page_rmw_lock
from ....graph.path_sandbox import read_graph_file_text, resolved_graph_root
from ....utils.secret_redaction import secret_violations_in_text
from ...outline_models import OutlineNode
from .convert import ConvertedJournalPlan, ConvertedPagePlan
from .link import TanaLinkResult
from .provenance import PROP_TANA_ID, iso_export_timestamp

TANA_LEDGER_PAGE = "Tana/Import Log"
_TANA_ID_PATTERN = re.compile(r"tana-id::\s*(\S+)")
_DEFAULT_TAB_SIZE = 2


@dataclass
class TanaWriteReport:
    """Dry-run or applied import write summary (JSON-serializable)."""

    apply: bool
    export_file: str | None = None
    export_ts: str = ""
    pages_created: list[str] = field(default_factory=list)
    pages_appended: list[str] = field(default_factory=list)
    journals_touched: list[str] = field(default_factory=list)
    skipped_duplicates: int = 0
    blocks_written: int = 0
    occ_conflicts: int = 0
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "apply": self.apply,
            "export_file": self.export_file,
            "export_ts": self.export_ts,
            "pages_created": list(self.pages_created),
            "pages_appended": list(self.pages_appended),
            "journals_touched": list(self.journals_touched),
            "skipped_duplicates": self.skipped_duplicates,
            "blocks_written": self.blocks_written,
            "occ_conflicts": self.occ_conflicts,
            "warnings": list(self.warnings),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


def scan_existing_tana_ids(graph_root: str | Path) -> set[str]:
    """Collect every ``tana-id::`` value already present under ``pages/`` and ``journals/``."""
    root = resolved_graph_root(graph_root)
    found: set[str] = set()
    for path in _iter_graph_markdown_paths(root):
        text = read_graph_file_text(path, root, errors="replace")
        found.update(_TANA_ID_PATTERN.findall(text))
    return found


def write_tana_import(
    linked: TanaLinkResult,
    graph_root: str | Path,
    *,
    apply: bool = False,
    export_file: str | None = None,
    existing_tana_ids: set[str] | None = None,
) -> TanaWriteReport:
    """Write entity pages, journals, and the import ledger from a linked convert result."""
    root = resolved_graph_root(graph_root)
    convert = linked.convert_result
    seen = set(existing_tana_ids) if existing_tana_ids is not None else scan_existing_tana_ids(root)
    export_ts = iso_export_timestamp()
    report = TanaWriteReport(apply=apply, export_file=export_file, export_ts=export_ts)

    for page in convert.pages:
        _write_page_plan(
            root,
            page,
            seen=seen,
            apply=apply,
            report=report,
        )

    for journal in convert.journals:
        _write_journal_plan(
            root,
            journal,
            seen=seen,
            apply=apply,
            report=report,
        )

    if apply:
        _append_ledger_entry(root, report=report)

    return report


def _iter_graph_markdown_paths(graph_root: Path) -> Iterator[Path]:
    for path in iter_scannable_pages_markdown(graph_root):
        yield path
    journals = graph_root / "journals"
    if journals.is_dir():
        for path in sorted(journals.rglob("*.md")):
            if path.is_file() and is_scannable_graph_markdown(path, graph_root):
                yield path


def _write_page_plan(
    graph_root: Path,
    page: ConvertedPagePlan,
    *,
    seen: set[str],
    apply: bool,
    report: TanaWriteReport,
) -> None:
    page_tana_id = page.page_properties.get(PROP_TANA_ID, "").strip()
    if page_tana_id and page_tana_id in seen:
        report.skipped_duplicates += 1
        return

    filtered_roots: list[OutlineNode] = []
    for root in page.outline_roots:
        filtered, skipped = _filter_outline_subtree(root, seen)
        report.skipped_duplicates += skipped
        if filtered is not None:
            filtered_roots.append(filtered)

    if not filtered_roots:
        if page_tana_id:
            report.skipped_duplicates += 1
        return

    markdown_body = _outline_to_markdown(filtered_roots)
    violations = secret_violations_in_text(markdown_body)
    if violations:
        report.warnings.append(
            f"secret scan blocked page {page.page_title}: {', '.join(violations)}",
        )
        return

    page_path = graph_safe_page_path(graph_root, page.page_title)
    is_new = not page_path.is_file()
    block_count = sum(_outline_node_count(node) for node in filtered_roots)

    if not apply:
        if is_new:
            report.pages_created.append(page.page_title)
        else:
            report.pages_appended.append(page.page_title)
        report.blocks_written += block_count
        _register_written_tana_ids(filtered_roots, seen)
        if page_tana_id:
            seen.add(page_tana_id)
        return

    written = _commit_page_markdown(
        graph_root,
        page_path,
        page_title=page.page_title,
        page_properties=page.page_properties,
        markdown_body=markdown_body,
        is_new=is_new,
        report=report,
    )
    if not written:
        return

    if is_new:
        report.pages_created.append(page.page_title)
    else:
        report.pages_appended.append(page.page_title)
    report.blocks_written += block_count
    _register_written_tana_ids(filtered_roots, seen)
    if page_tana_id:
        seen.add(page_tana_id)


def _write_journal_plan(
    graph_root: Path,
    journal: ConvertedJournalPlan,
    *,
    seen: set[str],
    apply: bool,
    report: TanaWriteReport,
) -> None:
    filtered_roots: list[OutlineNode] = []
    for root in journal.outline_roots:
        filtered, skipped = _filter_outline_subtree(root, seen)
        report.skipped_duplicates += skipped
        if filtered is not None:
            filtered_roots.append(filtered)

    if not filtered_roots:
        return

    markdown_body = _outline_to_markdown(filtered_roots)
    violations = secret_violations_in_text(markdown_body)
    if violations:
        report.warnings.append(
            f"secret scan blocked journal {journal.relative_path}: {', '.join(violations)}",
        )
        return

    journal_path = (graph_root / journal.relative_path).resolve()
    try:
        journal_path.relative_to(graph_root.resolve())
    except ValueError:
        report.warnings.append(f"journal path escapes graph root: {journal.relative_path}")
        return

    block_count = sum(_outline_node_count(node) for node in filtered_roots)

    if not apply:
        if journal.relative_path not in report.journals_touched:
            report.journals_touched.append(journal.relative_path)
        report.blocks_written += block_count
        _register_written_tana_ids(filtered_roots, seen)
        return

    written = _append_markdown_file(
        graph_root,
        journal_path,
        markdown_body,
        robot_summary=f"tana import journal {journal.page_title}",
        report=report,
    )
    if not written:
        return

    if journal.relative_path not in report.journals_touched:
        report.journals_touched.append(journal.relative_path)
    report.blocks_written += block_count
    _register_written_tana_ids(filtered_roots, seen)


def _commit_page_markdown(
    graph_root: Path,
    page_path: Path,
    *,
    page_title: str,
    page_properties: dict[str, str],
    markdown_body: str,
    is_new: bool,
    report: TanaWriteReport,
) -> bool:
    page_path.parent.mkdir(parents=True, exist_ok=True)
    robot_summary = f"tana import page {page_title}"

    if is_new:
        text = stamp_plumber_authored_page("")
        text = inject_page_properties(text, page_properties)
        if markdown_body.strip():
            text = text.rstrip() + ("\n\n" if text.strip() else "") + markdown_body.rstrip() + "\n"
        elif not text.endswith("\n"):
            text += "\n"
        with page_rmw_lock(page_path):
            atomic_write_bytes(
                page_path,
                text.encode("utf-8"),
                graph_root=graph_root,
                validate_block_refs=False,
                robot_commit_summary=robot_summary,
            )
        return True

    section = markdown_body.rstrip() + "\n"
    return _append_markdown_file(
        graph_root,
        page_path,
        section,
        robot_summary=robot_summary,
        report=report,
    )


def _append_markdown_file(
    graph_root: Path,
    path: Path,
    section: str,
    *,
    robot_summary: str,
    report: TanaWriteReport,
) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    section_text = section.rstrip() + "\n"

    with page_rmw_lock(path):
        prev = read_graph_file_text(path, graph_root, encoding="utf-8") if path.is_file() else ""
        new_text = prev.rstrip("\n") + ("\n\n" if prev.strip() else "") + section_text

        if path.is_file():
            occ = OCCSnapshot.capture(path)
            if occ is None:
                report.warnings.append(f"could not capture OCC snapshot for {path.name}")
                return False
            if occ.drifted():
                report.occ_conflicts += 1
                report.warnings.append(f"OCC drift aborted write for {path.name}")
                return False
            if not atomic_write_bytes_if_unchanged(
                path,
                new_text.encode("utf-8"),
                graph_root=graph_root,
                baseline_mtime=occ.baseline_mtime,
                validate_block_refs=False,
                robot_commit_summary=robot_summary,
            ):
                report.occ_conflicts += 1
                report.warnings.append(f"OCC conflict aborted write for {path.name}")
                return False
            occ.refresh_after_own_write()
        else:
            atomic_write_bytes(
                path,
                new_text.encode("utf-8"),
                graph_root=graph_root,
                validate_block_refs=False,
                robot_commit_summary=robot_summary,
            )
    return True


def _append_ledger_entry(graph_root: Path, *, report: TanaWriteReport) -> None:
    source = report.export_file or "unknown"
    counters = (
        f"pages_created:: {len(report.pages_created)}, "
        f"pages_appended:: {len(report.pages_appended)}, "
        f"journals_touched:: {len(report.journals_touched)}, "
        f"skipped_duplicates:: {report.skipped_duplicates}, "
        f"blocks_written:: {report.blocks_written}, "
        f"occ_conflicts:: {report.occ_conflicts}"
    )
    section = (
        f"- Tana import **{source}** at {report.export_ts}\n"
        f"  {counters}\n"
    )
    ledger_path = graph_safe_page_path(graph_root, TANA_LEDGER_PAGE)
    _append_markdown_file(
        graph_root,
        ledger_path,
        section,
        robot_summary=f"tana import ledger {source}",
        report=report,
    )


def _filter_outline_subtree(
    node: OutlineNode,
    seen: set[str],
) -> tuple[OutlineNode | None, int]:
    tana_id = _tana_id_from_node(node)
    if tana_id and tana_id in seen:
        return None, _outline_node_count(node)

    filtered_children: list[OutlineNode] = []
    skipped = 0
    for child in node.children:
        kept, child_skipped = _filter_outline_subtree(child, seen)
        skipped += child_skipped
        if kept is not None:
            filtered_children.append(kept)

    return node.model_copy(update={"children": filtered_children}), skipped


def _register_written_tana_ids(roots: list[OutlineNode], seen: set[str]) -> None:
    for root in roots:
        for node in _iter_outline_nodes(root):
            tana_id = _tana_id_from_node(node)
            if tana_id:
                seen.add(tana_id)


def _iter_outline_nodes(node: OutlineNode) -> Iterator[OutlineNode]:
    yield node
    for child in node.children:
        yield from _iter_outline_nodes(child)


def _tana_id_from_node(node: OutlineNode) -> str | None:
    raw = node.properties.get(PROP_TANA_ID, "").strip()
    return raw or None


def _outline_node_count(node: OutlineNode) -> int:
    return 1 + sum(_outline_node_count(child) for child in node.children)


def _outline_to_markdown(roots: list[OutlineNode], *, tab_size: int = _DEFAULT_TAB_SIZE) -> str:
    lines: list[str] = []
    for root in roots:
        _emit_outline_node(root, 0, lines, tab_size)
    return "".join(strip_line_endings(line) + canonical_line_suffix(line) for line in lines)


def _emit_outline_node(
    node: OutlineNode,
    indent_level: int,
    out_lines: list[str],
    tab_size: int,
) -> None:
    block_uuid = str(uuid.uuid4())
    bullet_indent = " " * (indent_level * tab_size)
    body_indent = " " * ((indent_level + 1) * tab_size)
    content_lines = node.text.splitlines()
    head = content_lines[0] if content_lines else ""
    out_lines.append(f"{bullet_indent}- {strip_line_endings(head)}\n")
    for extra in content_lines[1:]:
        out_lines.append(f"{body_indent}{strip_line_endings(extra)}\n")
    for prop in _property_lines(dict(node.properties), block_uuid):
        out_lines.append(f"{body_indent}{prop}\n")
    for child in node.children:
        _emit_outline_node(child, indent_level + 1, out_lines, tab_size)


def _property_lines(properties: dict[str, str], block_uuid: str) -> list[str]:
    lines: list[str] = []
    for key, value in properties.items():
        prop_key = key if key.endswith("::") else f"{key}::"
        lines.append(f"{prop_key} {value}")
    if not any(line.strip().startswith("id::") for line in lines):
        lines.append(f"id:: {block_uuid}")
    return lines


__all__ = [
    "TANA_LEDGER_PAGE",
    "TanaWriteReport",
    "scan_existing_tana_ids",
    "write_tana_import",
]
