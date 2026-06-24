"""Verify InstructorLLMClient routes system prompts through injected builders."""

from __future__ import annotations

from typing import Literal

import pytest
from src.agent.bootstrap.prompts import HarvestPromptBuilder
from src.agent.llm_client import InstructorLLMClient
from src.agent.plumber_llm import BootstrapSummaryResult
from src.agent.prompts.core import PromptContext


class _MarkerBuilder:
  tier: Literal["1A", "1B"] = "1A"

  def __init__(self, marker: str) -> None:
      self._marker = marker

  def build(self, ctx: PromptContext | None = None) -> str:
      _ = ctx
      return self._marker


def test_harvest_page_summary_uses_injected_builder_system_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = "INJECTED_HARVEST_SYSTEM_PROMPT_MARKER"
    client = InstructorLLMClient(
        base_url="http://127.0.0.1:9",
        api_key="test",
        model="test",
        harvest_builder=_MarkerBuilder(marker),
    )
    captured: list[str] = []

    def _fake_completion(
        *,
        prompt: str,
        response_model: type[BootstrapSummaryResult],
        system_prompt: str,
        stateless: bool = False,
        telemetry_target: str = "",
        telemetry_operation: str = "",
        thermal_profile: str = "cognitive",
        kv_prefix_hash: str | None = None,
        log_tokens: bool = True,
        use_history: bool = True,
    ) -> tuple[BootstrapSummaryResult, object]:
        _ = (
            prompt,
            response_model,
            stateless,
            telemetry_target,
            telemetry_operation,
            thermal_profile,
            kv_prefix_hash,
            log_tokens,
            use_history,
        )
        captured.append(system_prompt)
        return BootstrapSummaryResult(summary="ok", suggested_tags=[]), object()

    monkeypatch.setattr(client, "_completion_with_structured_output", _fake_completion)
    client.harvest_page_summary("Demo Page", "- bullet\n")
    assert captured == [marker]


def test_default_harvest_builder_matches_standalone_function() -> None:
    client = InstructorLLMClient(
        base_url="http://127.0.0.1:9",
        api_key="test",
        model="test",
    )
    assert isinstance(client._harvest_builder, HarvestPromptBuilder)
    assert client._harvest_builder.build() == HarvestPromptBuilder().build()
