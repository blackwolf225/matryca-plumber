"""Structured LLM payloads and protocol for Plumber cognitive modules."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from ..graph.cognitive_llm import (
    BootstrapSummaryResult,
    GraphInsightsLLMResult,
    HarvestLLM,
    InsightsLLM,
)

MarpaDomain = Literal["mappa", "area", "risorsa", "progetto", "archivio"]

_MatrycaLLMModel = ConfigDict(extra="forbid")


class MarpaClassificationResult(BaseModel):
    """LLM classification payload for the MARPA taxonomy framework."""

    model_config = _MatrycaLLMModel

    assigned_domain: MarpaDomain = Field(description="MARPA domain assignment")
    detected_tags: list[str] = Field(default_factory=list)
    inferred_properties: dict[str, str] = Field(default_factory=dict)
    violates_ssot_duplication: bool = Field(default=False)


class ContextualSeedResult(BaseModel):
    """Micro-definition for a newly seeded dangling-link page."""

    model_config = _MatrycaLLMModel

    definition: str = Field(description="Short contextual definition for the new page")


class EntityOverlapResult(BaseModel):
    """Semantic overlap assessment between two page concepts."""

    model_config = _MatrycaLLMModel

    overlap_score: float = Field(ge=0.0, le=1.0, description="0-1 semantic similarity")
    canonical_title: str = Field(description="Preferred canonical page title")
    alias_title: str = Field(description="Secondary title to register as alias")
    should_merge_alias: bool = Field(
        description="True when overlap_score exceeds threshold and alias should be added",
    )
    reason: str = Field(default="")


class InferredPropertiesResult(BaseModel):
    """Properties inferred for a tagged page."""

    model_config = _MatrycaLLMModel

    properties: dict[str, str] = Field(
        default_factory=dict,
        description="Logseq property keys (without ::) mapped to values",
    )


class PlumberModuleLLM(Protocol):
    """LLM surface used by cognitive lint modules."""

    def generate_contextual_seed(
        self,
        *,
        link_title: str,
        source_page: str,
        context: str,
        max_words: int,
    ) -> ContextualSeedResult: ...

    def assess_entity_overlap(
        self,
        *,
        canonical_title: str,
        alias_title: str,
        canonical_excerpt: str,
        alias_excerpt: str,
    ) -> EntityOverlapResult: ...

    def infer_page_properties(
        self,
        *,
        page_title: str,
        content: str,
    ) -> InferredPropertiesResult: ...

    def classify_marpa_page(
        self,
        *,
        page_title: str,
        content: str,
        namespace_hint: str | None,
        page_path: Path | None = None,
        graph_root: Path | None = None,
    ) -> MarpaClassificationResult: ...


__all__ = [
    "BootstrapSummaryResult",
    "GraphInsightsLLMResult",
    "HarvestLLM",
    "InsightsLLM",
    "PlumberModuleLLM",
    "ContextualSeedResult",
    "EntityOverlapResult",
    "InferredPropertiesResult",
    "MarpaClassificationResult",
    "MarpaDomain",
]
