"""Resolve provisional Tana wikilinks against in-export pages and ``MasterCatalog``."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal, Protocol

from ....graph.master_catalog import MasterCatalog
from ...outline_models import OutlineNode
from .convert import ConvertedPagePlan, TanaConvertResult
from .graph import TanaWorkspaceGraph
from .html import plain_text_from_tana_html
from .provenance import PROP_TANA_ID
from .schema import NodeDump

_WIKILINK = re.compile(r"\[\[([^\]#|]+)(?:\|([^\]]+))?\]\]")

ResolveKind = Literal["in_flight", "page_title", "alias", "unchanged"]


class CatalogResolver(Protocol):
    """Subset of ``MasterCatalog`` used for Tana link resolution."""

    def resolve_page_title(self, page_title: str) -> str | None: ...

    def resolve_alias(self, alias: str) -> str | None: ...


@dataclass
class TanaLinkStats:
    """Counters for wikilink resolution during one import pass."""

    in_flight_resolved: int = 0
    catalog_title_resolved: int = 0
    catalog_alias_resolved: int = 0
    unchanged: int = 0


@dataclass
class TanaLinkResult:
    """Linked convert output plus resolution counters."""

    convert_result: TanaConvertResult
    stats: TanaLinkStats = field(default_factory=TanaLinkStats)


def build_in_flight_page_map(
    result: TanaConvertResult,
    graph: TanaWorkspaceGraph | None = None,
) -> dict[str, str]:
    """Map casefolded wikilink targets to canonical titles for this import batch."""
    mapping: dict[str, str] = {}

    def register(alias: str, canonical: str) -> None:
        key = alias.strip()
        if not key:
            return
        fold = key.casefold()
        mapping.setdefault(fold, canonical)
        mapping.setdefault(canonical.casefold(), canonical)

    for page in result.pages:
        register(page.page_title, page.page_title)
        _register_node_label(page, graph, register)

    for journal in result.journals:
        register(journal.page_title, journal.page_title)
        for root in journal.outline_roots:
            tana_id = root.properties.get(PROP_TANA_ID)
            if tana_id and graph is not None:
                node = graph.nodes.get(tana_id)
                if node is not None:
                    label = _node_label(node)
                    if label:
                        register(label, journal.page_title)

    return mapping


def link_tana_convert_result(
    result: TanaConvertResult,
    catalog: MasterCatalog | CatalogResolver | None = None,
    *,
    graph: TanaWorkspaceGraph | None = None,
    in_flight: dict[str, str] | None = None,
) -> TanaLinkResult:
    """Rewrite ``[[...]]`` targets in-place across all outline trees."""
    flight_map = in_flight if in_flight is not None else build_in_flight_page_map(result, graph)
    linker = _TanaLinker(catalog=catalog, in_flight=flight_map)

    for page in result.pages:
        for root in page.outline_roots:
            _walk_outline(root, linker)

    for journal in result.journals:
        for root in journal.outline_roots:
            _walk_outline(root, linker)

    return TanaLinkResult(convert_result=result, stats=linker.stats)


def _register_node_label(
    page: ConvertedPagePlan,
    graph: TanaWorkspaceGraph | None,
    register: Callable[[str, str], None],
) -> None:
    tana_id = page.page_properties.get(PROP_TANA_ID)
    if not tana_id or graph is None:
        return
    node = graph.nodes.get(tana_id)
    if node is None:
        return
    label = _node_label(node)
    if label:
        register(label, page.page_title)


def _node_label(node: NodeDump) -> str:
    raw = node.props.get("name")
    if isinstance(raw, str):
        return plain_text_from_tana_html(raw)
    return ""


def _walk_outline(node: OutlineNode, linker: _TanaLinker) -> None:
    node.text = rewrite_wikilinks_in_text(node.text, linker.resolve)
    for key, value in list(node.properties.items()):
        if "[[" in value:
            node.properties[key] = rewrite_wikilinks_in_text(value, linker.resolve)
    for child in node.children:
        _walk_outline(child, linker)


def rewrite_wikilinks_in_text(
    text: str,
    resolve: Callable[[str], tuple[str, ResolveKind]],
) -> str:
    """Replace ``[[target]]`` / ``[[target|label]]`` using ``resolve(target)``."""

    def repl(match: re.Match[str]) -> str:
        target = match.group(1).strip()
        display = match.group(2)
        canonical, _kind = resolve(target)
        if canonical == target:
            return match.group(0)
        if display is not None:
            return f"[[{canonical}|{display}]]"
        return f"[[{canonical}]]"

    return _WIKILINK.sub(repl, text)


@dataclass
class _TanaLinker:
    catalog: MasterCatalog | CatalogResolver | None
    in_flight: dict[str, str]
    stats: TanaLinkStats = field(default_factory=TanaLinkStats)

    def resolve(self, target: str) -> tuple[str, ResolveKind]:
        stripped = target.strip()
        if not stripped:
            return target, "unchanged"

        in_flight_title = self.in_flight.get(stripped.casefold())
        if in_flight_title is not None:
            if in_flight_title != stripped:
                self.stats.in_flight_resolved += 1
                return in_flight_title, "in_flight"
            return stripped, "unchanged"

        if self.catalog is not None:
            by_title = self.catalog.resolve_page_title(stripped)
            if by_title is not None and by_title != stripped:
                self.stats.catalog_title_resolved += 1
                return by_title, "page_title"
            if by_title is not None:
                return stripped, "unchanged"

            by_alias = self.catalog.resolve_alias(stripped)
            if by_alias is not None and by_alias != stripped:
                self.stats.catalog_alias_resolved += 1
                return by_alias, "alias"
            if by_alias is not None:
                return stripped, "unchanged"

        self.stats.unchanged += 1
        return stripped, "unchanged"


__all__ = [
    "CatalogResolver",
    "TanaLinkResult",
    "TanaLinkStats",
    "build_in_flight_page_map",
    "link_tana_convert_result",
    "rewrite_wikilinks_in_text",
]
