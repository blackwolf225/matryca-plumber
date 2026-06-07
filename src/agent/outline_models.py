"""Shared outline validation models for MCP tools and headless graph dispatch."""

from __future__ import annotations

from typing import Any, Literal, Self, cast

from pydantic import BaseModel, Field, field_validator, model_validator

from .quality_gate import (
    outline_bounds_violations,
    outline_security_violations,
)

PageType = Literal["entity", "project", "knowledge", "hub", "feedback"]
Domain = Literal["tech", "business", "content", "ops"]
EntityType = Literal["person", "client", "tool", "service", "technology"]

_HEADING_LEVEL_PROP_KEYS = frozenset({"heading_level", "heading_level::"})


class OutlineNode(BaseModel):
    """Hierarchical outline node as accepted by agent tools (JSON-serializable)."""

    text: str = Field(..., description="Block text (Logseq outliner / Markdown body).")
    properties: dict[str, str] = Field(
        default_factory=dict,
        description="Optional Logseq-style properties (string keys/values).",
    )
    children: list[OutlineNode] = Field(default_factory=list)
    page_type: PageType | None = Field(
        default=None,
        description="Optional; merged into Logseq ``type::`` on this block when set.",
    )
    domain: Domain | None = Field(
        default=None,
        description="Optional; merged into ``domain::`` (required for knowledge nodes).",
    )
    entity_type: EntityType | None = Field(
        default=None,
        description="Optional; merged into ``entity-type::`` when ``page_type`` is entity.",
    )
    heading_level: str | None = Field(
        default=None,
        description="Parser/LLM heading depth metadata (1–6); not persisted as a Logseq property.",
    )

    @model_validator(mode="before")
    @classmethod
    def _normalize_heading_level_input(cls, data: Any) -> Any:  # noqa: ANN401
        """Hoist ``heading_level`` from ``properties`` and strip parser echo keys."""
        if not isinstance(data, dict):
            return data
        props = data.get("properties")
        if isinstance(props, dict):
            props_copy = dict(props)
            hoisted: Any = None
            for key in _HEADING_LEVEL_PROP_KEYS:
                if key in props_copy:
                    hoisted = props_copy.pop(key)
                    break
            if hoisted is not None and data.get("heading_level") is None:
                data = {**data, "heading_level": hoisted}
            if props_copy != props:
                data = {**data, "properties": props_copy}
        hl = data.get("heading_level")
        if isinstance(hl, (int, float)) and not isinstance(hl, bool):
            data = {**data, "heading_level": str(hl)}
        return data

    @field_validator("heading_level", mode="before")
    @classmethod
    def _coerce_heading_level(cls, value: Any) -> Any:  # noqa: ANN401
        """Accept LLM ``int`` heading depths (e.g. ``1``) as strings (``\"1\"``)."""
        if value is None:
            return None
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return str(value)
        return value

    @field_validator("properties", mode="before")
    @classmethod
    def _coerce_property_values(cls, value: Any) -> Any:  # noqa: ANN401
        """Stringify numeric/boolean property values echoed from parser JSON."""
        if value is None:
            return {}
        if not isinstance(value, dict):
            return value
        out: dict[str, Any] = {}
        for key, val in value.items():
            if isinstance(val, (int, float, bool)):
                out[key] = str(val)
            else:
                out[key] = val
        return out

    @field_validator("children", mode="before")
    @classmethod
    def _empty_children(cls, value: Any) -> list[Any]:  # noqa: ANN401
        """Treat ``null`` / missing children as an empty list."""
        if value is None:
            return []
        return cast(list[Any], value)

    @model_validator(mode="after")
    def _merge_schema_fields_into_properties(self) -> Self:
        """Mirror llm-wiki schema helpers into Logseq property lines."""
        explicit_schema = (
            self.page_type is not None or self.domain is not None or self.entity_type is not None
        )
        if not explicit_schema:
            return self

        merged = dict(self.properties)
        if self.page_type is not None:
            merged.setdefault("type::", self.page_type)
        if self.domain is not None:
            merged.setdefault("domain::", self.domain)
        if self.entity_type is not None:
            merged.setdefault("entity-type::", self.entity_type)

        ptype = merged.get("type::")
        dom = merged.get("domain::")
        ent = merged.get("entity-type::")
        if ptype == "entity" and not ent:
            msg = "entity blocks require `entity_type` or `properties['entity-type::']`"
            raise ValueError(msg)
        if ptype == "knowledge" and not dom:
            msg = "knowledge blocks require `domain` or `properties['domain::']`"
            raise ValueError(msg)

        if merged == self.properties:
            return self
        return self.model_copy(update={"properties": merged})


def outline_block_count(outline: dict[str, Any]) -> int:
    """Count nodes in a nested outline dict (including the root)."""
    n = 1
    raw = outline.get("children")
    children = raw if isinstance(raw, list) else []
    for ch in children:
        if isinstance(ch, dict):
            n += outline_block_count(cast(dict[str, Any], ch))
    return n


def validate_outline_for_write(outline: dict[str, Any]) -> OutlineNode:
    """Run bounds, security scan, and Pydantic validation (CPU-heavy; call via ``to_thread``)."""
    bounds = outline_bounds_violations(outline)
    if bounds:
        raise ValueError("; ".join(bounds))
    sec = outline_security_violations(outline)
    if sec:
        raise ValueError("; ".join(sec))
    return OutlineNode.model_validate(outline)


__all__ = [
    "Domain",
    "EntityType",
    "OutlineNode",
    "PageType",
    "outline_block_count",
    "validate_outline_for_write",
]
