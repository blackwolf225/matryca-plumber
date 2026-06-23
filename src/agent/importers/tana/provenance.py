"""Provenance helpers for Tana → Logseq conversion."""

from __future__ import annotations

from datetime import UTC, datetime

from .schema import NodeDump

PROP_TANA_ID = "tana-id"
PROP_TANA_CREATED = "tana-created"
PROP_TANA_MODIFIED = "tana-modified"
PROP_TANA_EXPORT = "tana-export"
PROP_TANA_EXPORT_FILE = "tana-export-file"
PROP_TANA_DEPTH_SPLIT = "tana-depth-split"


def iso_export_timestamp(*, as_of: datetime | None = None) -> str:
    moment = as_of or datetime.now(tz=UTC)
    return moment.replace(microsecond=0).isoformat()


def block_provenance_properties(
    node_id: str,
    node: NodeDump,
    *,
    export_ts: str | None = None,
    export_file: str | None = None,
    extra: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build block-level ``tana-*`` properties (never Logseq ``id::``)."""
    props: dict[str, str] = {PROP_TANA_ID: node_id}
    created = node.props.get("created")
    if isinstance(created, (int, float)):
        props[PROP_TANA_CREATED] = str(int(created))
    modified = node.props.get("modifiedTs")
    if isinstance(modified, list) and modified:
        props[PROP_TANA_MODIFIED] = str(modified[-1])
    elif isinstance(modified, (int, float)):
        props[PROP_TANA_MODIFIED] = str(int(modified))
    if export_ts:
        props[PROP_TANA_EXPORT] = export_ts
    if export_file:
        props[PROP_TANA_EXPORT_FILE] = export_file
    if extra:
        props.update(extra)
    return props


def page_provenance_properties(
    node_id: str,
    node: NodeDump,
    *,
    export_ts: str,
    export_file: str | None = None,
    depth_split: bool = False,
    tags: list[str] | None = None,
) -> dict[str, str]:
    """Frontmatter-style page properties for imported Tana pages."""
    props = block_provenance_properties(
        node_id,
        node,
        export_ts=export_ts,
        export_file=export_file,
    )
    tag_values = ["tana-import", *(tags or [])]
    props["tags"] = ", ".join(dict.fromkeys(tag_values))
    if depth_split:
        props[PROP_TANA_DEPTH_SPLIT] = "true"
    return props


__all__ = [
    "PROP_TANA_DEPTH_SPLIT",
    "PROP_TANA_EXPORT",
    "PROP_TANA_EXPORT_FILE",
    "PROP_TANA_ID",
    "block_provenance_properties",
    "iso_export_timestamp",
    "page_provenance_properties",
]
