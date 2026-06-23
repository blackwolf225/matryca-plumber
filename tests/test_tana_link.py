"""Tests for Tana wikilink resolution against in-flight pages and MasterCatalog."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.agent.importers.tana.convert import ConvertedPagePlan, TanaConvertResult
from src.agent.importers.tana.graph import TanaWorkspaceGraph
from src.agent.importers.tana.link import link_tana_convert_result
from src.agent.importers.tana.provenance import PROP_TANA_ID
from src.agent.importers.tana.schema import NodeDump
from src.agent.outline_models import OutlineNode


def _mock_catalog(
    *,
    page_titles: dict[str, str] | None = None,
    aliases: dict[str, str] | None = None,
) -> MagicMock:
    catalog = MagicMock()
    page_titles = page_titles or {}
    aliases = aliases or {}

    def resolve_page_title(title: str) -> str | None:
        return page_titles.get(title)

    def resolve_alias(alias: str) -> str | None:
        return aliases.get(alias)

    catalog.resolve_page_title.side_effect = resolve_page_title
    catalog.resolve_alias.side_effect = resolve_alias
    return catalog


def _convert_result_with_block(
    text: str,
    *,
    properties: dict[str, str] | None = None,
) -> TanaConvertResult:
    return TanaConvertResult(
        pages=[
            ConvertedPagePlan(
                page_title="Tana/Source",
                page_properties={PROP_TANA_ID: "SRC"},
                outline_roots=[
                    OutlineNode(
                        text=text,
                        properties=properties or {},
                    )
                ],
            )
        ]
    )


def test_catalog_alias_resolves_wikilink_in_block_text() -> None:
    catalog = _mock_catalog(aliases={"Alias Falso": "Pagina Vera"})
    result = _convert_result_with_block("See [[Alias Falso]] for details")

    linked = link_tana_convert_result(result, catalog)
    block = linked.convert_result.pages[0].outline_roots[0]

    assert block.text == "See [[Pagina Vera]] for details"
    assert linked.stats.catalog_alias_resolved == 1
    assert linked.stats.in_flight_resolved == 0


def test_in_flight_entity_resolves_before_catalog() -> None:
    catalog = _mock_catalog(page_titles={"Nuova Entita": "Existing Orphan"})
    graph = TanaWorkspaceGraph.from_nodes(
        {
            "ENT": NodeDump(
                id="ENT",
                props={"name": "Nuova Entita", "_flags": 1},
                children=[],
            ),
        }
    )
    convert = convert_tana_graph_for_link_test(graph)
    convert.pages[0].outline_roots[0].children = [
        OutlineNode(text="Link to [[Nuova Entita]]", properties={})
    ]

    linked = link_tana_convert_result(convert, catalog, graph=graph)
    child = linked.convert_result.pages[0].outline_roots[0].children[0]

    assert child.text == "Link to [[Tana/Nuova Entita]]"
    assert linked.stats.in_flight_resolved == 1
    catalog.resolve_page_title.assert_not_called()
    catalog.resolve_alias.assert_not_called()


def test_catalog_page_title_resolves_when_not_in_flight() -> None:
    catalog = _mock_catalog(page_titles={"vecchia pagina": "Pagina Canonica"})
    result = _convert_result_with_block("Ref [[vecchia pagina]]")

    linked = link_tana_convert_result(result, catalog)
    block = linked.convert_result.pages[0].outline_roots[0]

    assert block.text == "Ref [[Pagina Canonica]]"
    assert linked.stats.catalog_title_resolved == 1


def test_property_values_are_rewritten() -> None:
    catalog = _mock_catalog(aliases={"Alias Falso": "Pagina Vera"})
    result = _convert_result_with_block(
        "plain",
        properties={"related": "[[Alias Falso]]"},
    )

    linked = link_tana_convert_result(result, catalog)
    props = linked.convert_result.pages[0].outline_roots[0].properties

    assert props["related"] == "[[Pagina Vera]]"


def test_unresolved_link_left_unchanged() -> None:
    catalog = _mock_catalog()
    result = _convert_result_with_block("Orphan [[Missing Page]]")

    linked = link_tana_convert_result(result, catalog)
    block = linked.convert_result.pages[0].outline_roots[0]

    assert block.text == "Orphan [[Missing Page]]"
    assert linked.stats.unchanged == 1


def convert_tana_graph_for_link_test(graph: TanaWorkspaceGraph) -> TanaConvertResult:
    from src.agent.importers.tana.convert import convert_tana_graph

    return convert_tana_graph(graph, max_depth=8)
