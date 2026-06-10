"""Real-time graph telemetry for the Plumber UI dashboard."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from loguru import logger

from ..utils.bounded_json import BoundedJsonError, read_bounded_json
from .alias_index import (
    is_scannable_graph_markdown,
    iter_alias_source_paths,
    iter_scannable_pages_markdown,
)
from .generational_cache import cached_build_alias_index
from .link_tag_hop import _WIKILINK
from .master_catalog import MATRYCA_GENERATED_INDEX_TITLES, load_master_catalog
from .page_properties import is_plumber_authored_page
from .path_sandbox import read_graph_file_text

_CACHE_DIRNAME = ".matryca_semantic_cache"
_DEFAULT_CONTEXT_ACCELERATION = 0.0
# Align with Sovereign UI graph-analytics poll cadence (~20s at 4×5s cycles).
_ANALYTICS_TTL_SECONDS = 18.0
GraphAnalyticsStatus = Literal["online", "offline"]


@dataclass(frozen=True, slots=True)
class TelemetryLedgerSnapshot:
    """Reconciled daemon ledger counters after a live graph scan."""

    ai_links_injected: int
    ai_blocks_healed: int
    ai_pages_created: int
    page_summaries_created: int
    healed: bool = False


@dataclass(frozen=True, slots=True)
class GraphAnalytics:
    """Structural and semantic metrics computed from the live Logseq graph."""

    total_pages: int = 0
    total_journals: int = 0
    total_links: int = 0
    human_pages: int = 0
    human_journals: int = 0
    human_links: int = 0
    ai_pages: int = 0
    ai_links: int = 0
    ai_blocks_healed: int = 0
    page_summaries: int = 0
    alias_count: int = 0
    semantic_links: int = 0
    semantic_cache_mb: float = 0.0
    context_acceleration: float = _DEFAULT_CONTEXT_ACCELERATION
    status: GraphAnalyticsStatus = "online"

    def to_dict(self) -> dict[str, float | int | str]:
        return {
            "total_pages": self.total_pages,
            "total_journals": self.total_journals,
            "total_links": self.total_links,
            "human_pages": self.human_pages,
            "human_journals": self.human_journals,
            "human_links": self.human_links,
            "ai_pages": self.ai_pages,
            "ai_links": self.ai_links,
            "ai_blocks_healed": self.ai_blocks_healed,
            "page_summaries": self.page_summaries,
            "alias_count": self.alias_count,
            "semantic_links": self.semantic_links,
            "semantic_cache_mb": self.semantic_cache_mb,
            "context_acceleration": self.context_acceleration,
            "status": self.status,
        }


def offline_graph_analytics(
    *,
    ai_links_injected: int = 0,
    ai_blocks_healed: int = 0,
) -> GraphAnalytics:
    """Safe zeroed telemetry when the graph root is temporarily inaccessible."""
    return GraphAnalytics(
        ai_links=ai_links_injected,
        ai_blocks_healed=ai_blocks_healed,
        status="offline",
    )


_analytics_cache: dict[str, tuple[float, GraphAnalytics]] = {}


def _count_journal_metrics(graph_root: Path) -> tuple[int, int]:
    """Return ``(total_journals, ai_journals)`` under ``journals/``."""
    journals = graph_root / "journals"
    if not journals.is_dir():
        return 0, 0
    total = 0
    ai = 0
    for path in journals.rglob("*.md"):
        if not path.is_file() or not is_scannable_graph_markdown(path, graph_root):
            continue
        total += 1
        try:
            text = read_graph_file_text(path, graph_root, errors="replace")
        except OSError:
            continue
        if is_plumber_authored_page(text):
            ai += 1
    return total, ai


def _count_catalog_summaries(graph_root: Path) -> int:
    """Count master-catalog rows with a non-empty Phase 1 summary."""
    root = graph_root.expanduser().resolve(strict=False)
    try:
        catalog = load_master_catalog(root)
    except Exception:
        return 0
    return sum(
        1
        for title, entry in catalog.pages.items()
        if title not in MATRYCA_GENERATED_INDEX_TITLES and entry.summary.strip()
    )


def _count_links_scanned(graph_root: Path) -> int:
    total = 0
    for path in iter_alias_source_paths(graph_root):
        try:
            text = read_graph_file_text(path, graph_root, errors="replace")
        except OSError:
            continue
        total += len(_WIKILINK.findall(text))
    return total


def _semantic_cache_size_mb(graph_root: Path) -> float:
    cache_dir = graph_root / _CACHE_DIRNAME
    if not cache_dir.is_dir():
        return 0.0
    total_bytes = 0
    for path in cache_dir.rglob("*"):
        if not path.is_file():
            continue
        try:
            total_bytes += path.stat().st_size
        except OSError:
            continue
    return round(total_bytes / (1024 * 1024), 1)


def _context_acceleration_rate(graph_root: Path, total_pages: int) -> float:
    cache_dir = graph_root / _CACHE_DIRNAME
    if not cache_dir.is_dir() or total_pages <= 0:
        return _DEFAULT_CONTEXT_ACCELERATION

    now = time.time()
    valid_entries = 0
    for path in cache_dir.glob("*.json"):
        try:
            raw = read_bounded_json(path)
        except BoundedJsonError:
            continue
        if not isinstance(raw, dict):
            continue
        try:
            created = float(raw.get("created_at", 0.0))
            ttl = int(raw.get("ttl_seconds", 86_400))
        except (TypeError, ValueError):
            continue
        if now - created <= ttl:
            valid_entries += 1

    if valid_entries == 0:
        return _DEFAULT_CONTEXT_ACCELERATION

    return round(min(99.9, (valid_entries / total_pages) * 100.0), 1)


def _count_blocks_scanned(graph_root: Path) -> int:
    total = 0
    for path in iter_alias_source_paths(graph_root):
        try:
            text = read_graph_file_text(path, graph_root, errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            if line.lstrip().startswith("- "):
                total += 1
    return total


def reconcile_telemetry_ledger(
    graph_root: Path,
    *,
    ai_links_injected: int,
    ai_blocks_healed: int,
    ai_pages_created: int = 0,
    page_summaries_created: int = 0,
) -> TelemetryLedgerSnapshot:
    """Clamp ledger counters when mass-deletions drop absolute graph totals below them."""
    root = graph_root.expanduser().resolve(strict=False)
    total_pages = len(iter_scannable_pages_markdown(root))
    total_links = _count_links_scanned(root)
    total_blocks = _count_blocks_scanned(root)

    healed = False
    links = ai_links_injected
    blocks = ai_blocks_healed
    pages = ai_pages_created
    summaries = page_summaries_created
    catalog_summaries = _count_catalog_summaries(root)

    if links > total_links:
        links = total_links
        healed = True
    if blocks > total_blocks:
        blocks = total_blocks
        healed = True
    if pages > total_pages:
        pages = total_pages
        healed = True
    if summaries > catalog_summaries and catalog_summaries > 0:
        summaries = catalog_summaries
        healed = True

    return TelemetryLedgerSnapshot(
        ai_links_injected=links,
        ai_blocks_healed=blocks,
        ai_pages_created=pages,
        page_summaries_created=summaries,
        healed=healed,
    )


def _count_current_ai_pages(graph_root: Path) -> int:
    total = 0
    for path in iter_scannable_pages_markdown(graph_root):
        try:
            text = read_graph_file_text(path, graph_root, errors="replace")
        except OSError:
            continue
        if is_plumber_authored_page(text):
            total += 1
    return total


def _compute_graph_analytics_uncached(
    graph_root: Path,
    *,
    ai_links_injected: int = 0,
    ai_blocks_healed: int = 0,
    page_summaries_created: int = 0,
) -> GraphAnalytics:
    root = graph_root.expanduser().resolve(strict=False)
    catalog_summaries = _count_catalog_summaries(root)
    page_summaries = max(catalog_summaries, page_summaries_created)
    total_pages_scanned = len(iter_scannable_pages_markdown(root))
    current_ai_pages = _count_current_ai_pages(root)
    total_links_scanned = _count_links_scanned(root)
    human_pages = max(0, total_pages_scanned - current_ai_pages)
    total_journals, ai_journals = _count_journal_metrics(root)
    human_journals = max(0, total_journals - ai_journals)
    human_links = max(0, total_links_scanned - ai_links_injected)
    alias_index = cached_build_alias_index(root)
    return GraphAnalytics(
        total_pages=total_pages_scanned,
        total_journals=total_journals,
        total_links=total_links_scanned,
        human_pages=human_pages,
        human_journals=human_journals,
        human_links=human_links,
        ai_pages=current_ai_pages,
        ai_links=ai_links_injected,
        ai_blocks_healed=ai_blocks_healed,
        page_summaries=page_summaries,
        alias_count=len(alias_index.alias_to_page),
        semantic_links=total_links_scanned,
        semantic_cache_mb=_semantic_cache_size_mb(root),
        context_acceleration=_context_acceleration_rate(root, total_pages_scanned),
    )


def _topology_revision(graph_root: Path) -> tuple[int, int]:
    """Cheap filesystem fingerprint so cache busts when pages or links change."""
    page_count = 0
    revision_ns = 0
    for path in iter_scannable_pages_markdown(graph_root):
        page_count += 1
        try:
            revision_ns += path.stat().st_mtime_ns
        except OSError:
            continue
    for path in iter_alias_source_paths(graph_root):
        try:
            revision_ns += path.stat().st_mtime_ns
        except OSError:
            continue
    return page_count, revision_ns


def compute_graph_analytics(
    graph_root: Path,
    *,
    ai_links_injected: int = 0,
    ai_blocks_healed: int = 0,
    page_summaries_created: int = 0,
) -> GraphAnalytics:
    """Return graph telemetry, reusing a short-lived in-process cache for UI polling."""
    root = graph_root.expanduser().resolve(strict=False)
    if not root.exists():
        logger.error("Graph analytics offline: graph root does not exist: {}", root)
        return offline_graph_analytics(
            ai_links_injected=ai_links_injected,
            ai_blocks_healed=ai_blocks_healed,
        )

    try:
        page_count, revision_ns = _topology_revision(root)
    except (OSError, FileNotFoundError) as exc:
        logger.error("Graph analytics offline during topology scan of {}: {}", root, exc)
        return offline_graph_analytics(
            ai_links_injected=ai_links_injected,
            ai_blocks_healed=ai_blocks_healed,
        )

    key = (
        f"{root}|{page_count}|{revision_ns}|{ai_links_injected}|"
        f"{ai_blocks_healed}|{page_summaries_created}"
    )
    now = time.monotonic()
    cached = _analytics_cache.get(key)
    if cached is not None and now - cached[0] < _ANALYTICS_TTL_SECONDS:
        return cached[1]

    try:
        result = _compute_graph_analytics_uncached(
            root,
            ai_links_injected=ai_links_injected,
            ai_blocks_healed=ai_blocks_healed,
            page_summaries_created=page_summaries_created,
        )
    except (OSError, FileNotFoundError) as exc:
        logger.error("Graph analytics offline during scan of {}: {}", root, exc)
        return offline_graph_analytics(
            ai_links_injected=ai_links_injected,
            ai_blocks_healed=ai_blocks_healed,
        )

    _analytics_cache[key] = (now, result)
    return result


__all__ = [
    "GraphAnalytics",
    "GraphAnalyticsStatus",
    "TelemetryLedgerSnapshot",
    "compute_graph_analytics",
    "offline_graph_analytics",
    "reconcile_telemetry_ledger",
]
