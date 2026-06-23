"""Decode Tana supertags, field tuples, and ``SYS_D*`` values → Logseq properties."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from loguru import logger

from .graph import TanaWorkspaceGraph
from .html import plain_text_from_tana_html
from .journal import format_journal_page_title
from .schema import NodeDump

_MEGA_TUPLE_CHILD_LIMIT = 50
_TYPE_CHOICE_SOURCE = "SYS_A02"

# Tana schema data-type codes (field definition ``typeChoice`` grandchildren).
SYS_D_CHECKBOX = "SYS_D01"
SYS_D_DATE = "SYS_D03"
SYS_D_REFERENCE = "SYS_D05"
SYS_D_TEXT = "SYS_D06"
SYS_D_NUMBER = "SYS_D08"
SYS_D_URL = "SYS_D10"
SYS_D_EMAIL = "SYS_D11"
SYS_D_OPTIONS = "SYS_D12"
SYS_D_USER = "SYS_D13"

_DAY_FIELD_KEYS = frozenset(
    {
        "date",
        "day",
        "due-date",
        "due",
        "deadline",
        "scheduled",
        "target-date",
    }
)
_SOURCE_FIELD_KEYS = frozenset({"source", "url", "link", "website", "href", "uri"})
_NON_KEY_CHAR = re.compile(r"[^a-z0-9-]+")
_MULTI_HYPHEN = re.compile(r"-+")


@dataclass(frozen=True, slots=True)
class LogseqPropertyLine:
    """One Logseq ``key:: value`` pair extracted from a Tana field tuple."""

    key: str
    value: str
    tana_tuple_id: str | None = None
    tana_field_def_id: str | None = None
    data_type: str | None = None


@dataclass
class NodeFieldExtraction:
    """Field metadata extracted for one Tana data node."""

    properties: list[LogseqPropertyLine] = field(default_factory=list)
    supertag_names: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class _FieldDef:
    field_id: str
    label: str
    normalized_key: str
    data_type: str


class TanaTagsExtractor:
    """Walk ``_metaNodeId`` chains and decode field tuples into Logseq properties."""

    def __init__(
        self,
        graph: TanaWorkspaceGraph,
        *,
        journal_page_title_format: str = "yyyy-MM-dd",
    ) -> None:
        self._graph = graph
        self._journal_format = journal_page_title_format
        self._field_defs = _build_field_def_index(graph)
        self._field_defs_by_key = {
            spec.normalized_key: spec for spec in self._field_defs.values()
        }

    def extract_for_node(self, node_id: str) -> NodeFieldExtraction:
        """Extract supertags and field properties for a Tana data node."""
        out = NodeFieldExtraction()
        node = self._graph.nodes.get(node_id)
        if node is None:
            return out

        meta_id = node.props.get("_metaNodeId")
        if not isinstance(meta_id, str):
            return out

        meta = self._graph.nodes.get(meta_id)
        if meta is None:
            out.warnings.append(f"missing metaNode {meta_id} for node {node_id}")
            return out

        for child_id in meta.children:
            child = self._graph.nodes.get(child_id)
            if child is None:
                continue
            if child.props.get("_docType") == "tuple":
                if _is_tag_application_tuple(child, self._graph):
                    tag_name = _tag_name_from_tuple(child, self._graph)
                    if tag_name and tag_name not in out.supertag_names:
                        out.supertag_names.append(tag_name)
                    continue
                props, warnings = self._extract_field_tuple(child)
                out.properties.extend(props)
                out.warnings.extend(warnings)
        return out

    def _extract_field_tuple(
        self,
        tuple_node: NodeDump,
    ) -> tuple[list[LogseqPropertyLine], list[str]]:
        warnings: list[str] = []
        if len(tuple_node.children) > _MEGA_TUPLE_CHILD_LIMIT:
            msg = (
                f"Skipping mega-tuple {tuple_node.id} with "
                f"{len(tuple_node.children)} children (limit {_MEGA_TUPLE_CHILD_LIMIT})"
            )
            logger.warning(msg)
            warnings.append(msg)
            return [], warnings

        if len(tuple_node.children) < 2:
            return [], warnings

        label_id = tuple_node.children[0]
        value_ids = tuple_node.children[1:]
        label_node = self._graph.nodes.get(label_id)
        if label_node is None:
            warnings.append(f"tuple {tuple_node.id} missing label child {label_id}")
            return [], warnings

        label_text = _node_plain_name(label_node)
        field_def = _resolve_field_def(
            tuple_node,
            label_text,
            self._field_defs,
            self._field_defs_by_key,
        )
        prop_key = (
            field_def.normalized_key if field_def else normalize_logseq_property_key(label_text)
        )
        data_type = field_def.data_type if field_def else SYS_D_TEXT

        values: list[str] = []
        for value_id in value_ids:
            value_node = self._graph.nodes.get(value_id)
            if value_node is None:
                continue
            rendered = _format_field_value(
                data_type,
                value_node,
                self._graph,
                prop_key=prop_key,
                journal_format=self._journal_format,
            )
            if rendered is not None:
                values.append(rendered)

        if not values:
            return [], warnings

        merged_value = ", ".join(values)
        final_key = prop_key
        if data_type == SYS_D_URL and (
            final_key in _SOURCE_FIELD_KEYS
            or final_key.startswith("source")
            or final_key.endswith("-url")
        ):
            final_key = "source"

        line = LogseqPropertyLine(
            key=final_key,
            value=merged_value,
            tana_tuple_id=tuple_node.id,
            tana_field_def_id=field_def.field_id if field_def else _coerce_source_id(tuple_node),
            data_type=data_type,
        )
        return [line], warnings


def normalize_logseq_property_key(label: str) -> str:
    """Normalize a Tana field label to a Logseq property key (no ``::`` suffix)."""
    plain = plain_text_from_tana_html(label).strip().lower()
    plain = plain.replace("_", "-").replace(" ", "-")
    plain = _NON_KEY_CHAR.sub("-", plain)
    plain = _MULTI_HYPHEN.sub("-", plain).strip("-")
    return plain or "field"


def format_property_line(prop: LogseqPropertyLine) -> str:
    """Render ``key:: value`` for Logseq OG block properties."""
    return f"{prop.key}:: {prop.value}"


def _build_field_def_index(graph: TanaWorkspaceGraph) -> dict[str, _FieldDef]:
    out: dict[str, _FieldDef] = {}
    for node_id, node in graph.nodes.items():
        if node.props.get("_docType") != "attrDef":
            continue
        label = _node_plain_name(node)
        if not label:
            continue
        data_type = _attr_def_data_type(node, graph) or SYS_D_TEXT
        normalized = normalize_logseq_property_key(label)
        out[node_id] = _FieldDef(
            field_id=node_id,
            label=label,
            normalized_key=normalized,
            data_type=data_type,
        )
    return out


def _attr_def_data_type(attr_def: NodeDump, graph: TanaWorkspaceGraph) -> str | None:
    for child_id in attr_def.children:
        child = graph.nodes.get(child_id)
        if child is None:
            continue
        if child.props.get("_sourceId") != _TYPE_CHOICE_SOURCE:
            continue
        for grandchild_id in child.children:
            code = grandchild_id if grandchild_id.startswith("SYS_D") else None
            if code is not None:
                return code
            grand = graph.nodes.get(grandchild_id)
            if grand is not None and grand.id.startswith("SYS_D"):
                return grand.id
    return None


def _resolve_field_def(
    tuple_node: NodeDump,
    label_text: str,
    field_defs: dict[str, _FieldDef],
    field_defs_by_key: dict[str, _FieldDef],
) -> _FieldDef | None:
    source_id = _coerce_source_id(tuple_node)
    if source_id and source_id in field_defs:
        return field_defs[source_id]
    normalized = normalize_logseq_property_key(label_text)
    return field_defs_by_key.get(normalized)


def _coerce_source_id(tuple_node: NodeDump) -> str | None:
    raw = tuple_node.props.get("_sourceId")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def _is_tag_application_tuple(tuple_node: NodeDump, graph: TanaWorkspaceGraph) -> bool:
    if not tuple_node.children:
        return False
    return all(graph.tag_def_names.get(child_id) for child_id in tuple_node.children)


def _tag_name_from_tuple(tuple_node: NodeDump, graph: TanaWorkspaceGraph) -> str | None:
    for child_id in tuple_node.children:
        name = graph.tag_def_names.get(child_id)
        if name:
            return name
    return None


def _node_plain_name(node: NodeDump) -> str:
    raw = node.props.get("name")
    if isinstance(raw, str):
        return plain_text_from_tana_html(raw)
    return ""


def _format_field_value(
    data_type: str,
    value_node: NodeDump,
    graph: TanaWorkspaceGraph,
    *,
    prop_key: str,
    journal_format: str,
) -> str | None:
    if data_type == SYS_D_CHECKBOX:
        return _format_checkbox_value(value_node)
    if data_type == SYS_D_DATE:
        return _format_date_value(value_node, prop_key=prop_key, journal_format=journal_format)
    if data_type == SYS_D_REFERENCE:
        return _format_reference_value(value_node, graph)
    if data_type == SYS_D_URL:
        return _format_url_value(value_node)
    if data_type == SYS_D_NUMBER:
        return _format_number_value(value_node)
    if data_type == SYS_D_EMAIL:
        return _format_text_value(value_node)
    return _format_text_value(value_node)


def _format_checkbox_value(value_node: NodeDump) -> str:
    done = value_node.props.get("_done")
    if done is True or (isinstance(done, (int, float)) and done):
        return "true"
    if value_node.props.get("done") is True:
        return "true"
    text = _node_plain_name(value_node).casefold()
    if text in {"true", "yes", "x", "checked", "done", "1"}:
        return "true"
    return "false"


def _format_date_value(value_node: NodeDump, *, prop_key: str, journal_format: str) -> str | None:
    iso = _extract_iso_date(value_node)
    if iso is None:
        text = _node_plain_name(value_node)
        return text or None
    if prop_key in _DAY_FIELD_KEYS:
        return f"[[{format_journal_page_title(iso, journal_format)}]]"
    return iso.isoformat()


def _extract_iso_date(value_node: NodeDump) -> date | None:
    created = value_node.props.get("created")
    if isinstance(created, (int, float)) and created > 0:
        return datetime.fromtimestamp(created / 1000, tz=UTC).date()
    text = _node_plain_name(value_node)
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def _format_reference_value(value_node: NodeDump, graph: TanaWorkspaceGraph) -> str | None:
    for ref_id in value_node.outbound_refs or value_node.children:
        target = graph.nodes.get(ref_id)
        if target is None:
            continue
        title = _node_plain_name(target)
        if title:
            return f"[[{title}]]"
    title = _node_plain_name(value_node)
    if title:
        return f"[[{title}]]"
    return None


def _format_url_value(value_node: NodeDump) -> str | None:
    text = _node_plain_name(value_node)
    if text.startswith(("http://", "https://")):
        return text
    for key in ("url", "href", "source"):
        raw = value_node.props.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return text or None


def _format_number_value(value_node: NodeDump) -> str | None:
    for key in ("value", "number", "amount"):
        raw = value_node.props.get(key)
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            return str(raw)
    text = _node_plain_name(value_node)
    return text or None


def _format_text_value(value_node: NodeDump) -> str | None:
    text = _node_plain_name(value_node)
    return text or None


__all__ = [
    "LogseqPropertyLine",
    "NodeFieldExtraction",
    "SYS_D_CHECKBOX",
    "SYS_D_DATE",
    "SYS_D_REFERENCE",
    "SYS_D_TEXT",
    "SYS_D_URL",
    "TanaTagsExtractor",
    "format_property_line",
    "normalize_logseq_property_key",
]
