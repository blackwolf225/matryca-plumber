"""Graph-layer LLM protocols and structured payloads for harvest and insights."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

_MatrycaLLMModel = ConfigDict(extra="forbid")


class BootstrapSummaryResult(BaseModel):
    """Minimal structured payload for bootstrap catalog harvesting."""

    model_config = _MatrycaLLMModel

    summary: str = Field(description="One-sentence page summary")
    suggested_tags: list[str] = Field(default_factory=list)
    domain: str = Field(default="", description="MARPA domain when inferable")


class GraphInsightsLLMResult(BaseModel):
    """Structured LLM payload for the graph insights dashboard."""

    model_config = _MatrycaLLMModel

    ontology_report: str = Field(
        description="Panoramic review of hidden conceptual clusters (markdown prose)",
    )
    cleanup_suggestions: list[str] = Field(
        default_factory=list,
        description="Non-destructive cleanup recommendations as short bullet texts",
    )


class HarvestLLM(Protocol):
    """LLM surface for bootstrap catalog harvesting."""

    def harvest_page_summary(
        self,
        page_title: str,
        content: str,
        *,
        page_path: Path | None = None,
        graph_root: Path | None = None,
        task_instruction: str | None = None,
    ) -> BootstrapSummaryResult: ...


class InsightsLLM(Protocol):
    """LLM surface for graph insights generation."""

    def generate_graph_insights(
        self,
        *,
        metrics_json: str,
        graph_root: Path,
    ) -> GraphInsightsLLMResult: ...


__all__ = [
    "BootstrapSummaryResult",
    "GraphInsightsLLMResult",
    "HarvestLLM",
    "InsightsLLM",
]
