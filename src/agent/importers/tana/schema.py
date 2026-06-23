"""Pydantic models for Tana raw workspace JSON node dumps."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NodeDump(BaseModel):
    """One element from the flat ``docs[]`` array in a Tana workspace export."""

    model_config = ConfigDict(extra="allow")

    id: str
    props: dict[str, Any] = Field(default_factory=dict)
    children: list[str] = Field(default_factory=list)
    inbound_refs: list[str] = Field(default_factory=list)
    outbound_refs: list[str] = Field(default_factory=list)

    @field_validator("children", "inbound_refs", "outbound_refs", mode="before")
    @classmethod
    def _coerce_id_list(cls, value: Any) -> list[str]:  # noqa: ANN401
        if value is None:
            return []
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if item is not None]

    @field_validator("props", mode="before")
    @classmethod
    def _coerce_props(cls, value: Any) -> dict[str, Any]:  # noqa: ANN401
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        return {}
