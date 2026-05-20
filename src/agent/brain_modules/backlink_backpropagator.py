"""Contextual backlink backpropagation for auto_wikilink semantic corrections."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ...graph.generational_cache import patch_generational_caches_for_paths
from ...graph.markdown_blocks import atomic_write_bytes
from ...graph.page_write_lock import page_rmw_lock
from ._shared import ModuleOutcome, page_file_exists, resolve_page_path

_BACKLINK_HEADER = "### Matryca Backlink Context"
_WIKILINK = re.compile(r"\[\[([^\]#|]+)(?:\|[^\]]+)?\]\]")
LintType = Literal["auto_wikilink", "tag_hygiene", "anomaly_warning"]


@dataclass
class BacklinkCorrection:
    """Minimal correction record for backprop (avoids circular imports)."""

    block_uuid: str
    original_text: str
    corrected_text: str
    lint_type: LintType
    reason: str


def _new_wikilinks(original: str, corrected: str) -> list[str]:
    orig = {m.group(1).strip() for m in _WIKILINK.finditer(original)}
    added: list[str] = []
    for match in _WIKILINK.finditer(corrected):
        target = match.group(1).strip()
        if target and target not in orig:
            added.append(target)
    return added


def _summary_from_correction(correction: BacklinkCorrection, source_title: str) -> str:
    if correction.reason.strip():
        return correction.reason.strip()
    return (
        f"[[{source_title}]] mentions this concept via auto_wikilink "
        f"({correction.original_text[:80]} → {correction.corrected_text[:80]})"
    )


def _backlink_block_exists(content: str, source_title: str) -> bool:
    needle = f"referenced-from:: [[{source_title}]]"
    return needle in content


def _format_backlink_section(source_title: str, target_title: str, summary: str) -> str:
    return (
        f"\n{_BACKLINK_HEADER}\n"
        f"- referenced-from:: [[{source_title}]]\n"
        f"- referenced-to:: [[{target_title}]]\n"
        f"- context-summary:: {summary.strip()}\n"
        f"- matryca-backprop:: true\n"
    )


def run_backlink_backpropagator(
    graph_root: Path,
    source_page: Path,
    source_title: str,
    corrections: list[BacklinkCorrection],
    applied_details: list[str],
) -> ModuleOutcome:
    """Append inverse context blocks on target pages for applied auto_wikilinks.

    Lock ordering: callers must release the source page lock before invoking this
    function. Each target page is locked independently (never nested with the source
    transaction) so cross-page backprop cannot deadlock with the semantic lint pass.
    """
    _ = source_page
    outcome = ModuleOutcome()
    applied_uuids = {
        detail.split(":", 2)[1] for detail in applied_details if detail.startswith("auto_wikilink:")
    }
    if not applied_uuids:
        return outcome

    for correction in corrections:
        if correction.lint_type != "auto_wikilink":
            continue
        if correction.block_uuid not in applied_uuids:
            continue
        for target in _new_wikilinks(correction.original_text, correction.corrected_text):
            if target == source_title:
                continue
            if not page_file_exists(graph_root, target):
                continue
            target_path = resolve_page_path(graph_root, target)
            if target_path is None:
                continue
            summary = _summary_from_correction(correction, source_title)
            modified = False
            with page_rmw_lock(target_path):
                prev = target_path.read_text(encoding="utf-8", errors="replace")
                if _backlink_block_exists(prev, source_title):
                    continue
                section = _format_backlink_section(source_title, target, summary)
                new_text = prev.rstrip("\n") + section
                atomic_write_bytes(target_path, new_text.encode("utf-8"), graph_root=graph_root)
                modified = True
            if modified:
                outcome.pages_modified.append(target)
                outcome.details.append(f"backprop:{source_title}->{target}")
                patch_generational_caches_for_paths(graph_root, [target_path])

    return outcome


__all__ = ["BacklinkCorrection", "run_backlink_backpropagator"]
