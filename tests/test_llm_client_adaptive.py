"""Tests for adaptive structured-output LLM client."""

from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, ValidationError
from src.agent.context_compressor import ChatMessage
from src.agent.llm_client import (
    GrammarCapability,
    InstructorLLMClient,
    LlmBackendProfile,
    StructuredOutputExhaustedError,
    append_correction_turn,
    llm_completion_token_limit_kwargs,
    pydantic_to_strict_json_schema,
)
from src.agent.outline_models import OutlineNode
from src.agent.plumber_config import DEFAULT_LLM_MAX_COMPRESSION_TOKENS
from src.agent.plumber_llm import GraphInsightsLLMResult


def test_pydantic_to_strict_json_schema_marks_nested_objects_strict() -> None:
    schema = pydantic_to_strict_json_schema(OutlineNode)
    outline_def = schema["$defs"]["OutlineNode"]
    assert schema.get("additionalProperties") is False
    assert outline_def.get("additionalProperties") is False


def test_llm_completion_token_limit_kwargs_prefers_legacy_for_local_models() -> None:
    assert llm_completion_token_limit_kwargs(model="qwen3-8b", limit=512) == {"max_tokens": 512}


def test_llm_completion_token_limit_kwargs_uses_openai_key_for_o_series() -> None:
    assert llm_completion_token_limit_kwargs(model="o1-preview", limit=128) == {
        "max_completion_tokens": 128,
    }


def test_outline_node_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        OutlineNode.model_validate({"text": "Note", "unexpected_field": "nope"})


def test_append_correction_turn_strips_degenerate_error_tail() -> None:
    messages: list[ChatMessage] = [{"role": "system", "content": "sys"}]
    error = "validation failed" + ("\\n" * 80)
    updated = append_correction_turn(messages, error=error)
    assert "\\n\\n\\n" not in updated[-1]["content"]
    assert "validation failed" in updated[-1]["content"]


def test_append_correction_turn_adds_user_message() -> None:
    messages: list[ChatMessage] = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "go"},
    ]
    updated = append_correction_turn(messages, error="field required")
    assert updated[-1]["role"] == "user"
    assert "field required" in updated[-1]["content"]


def test_path_a_single_completion(monkeypatch: pytest.MonkeyPatch) -> None:
    client = InstructorLLMClient(base_url="http://localhost:1234/v1")
    engine = client._structured_engine
    profile = LlmBackendProfile(
        base_url=client.base_url,
        model=client.model,
        grammar_capability=GrammarCapability.LOGITS_JSON_SCHEMA,
        probed_at=0.0,
    )
    monkeypatch.setattr(engine, "probe_backend", lambda **_: profile)

    class Tiny(BaseModel):
        value: str = "ok"

    response = MagicMock()
    response.choices = [
        MagicMock(message=MagicMock(content='{"value": "ok"}')),
    ]
    response.usage = None
    create_mock = MagicMock(return_value=response)
    monkeypatch.setattr(client._raw_client.chat.completions, "create", create_mock)

    messages: list[ChatMessage] = [
        {"role": "system", "content": "s"},
        {"role": "user", "content": "u"},
    ]
    parsed, _ = engine.completion_structured(
        messages=messages,
        response_model=Tiny,
        prompt="u",
        started=0.0,
        use_history=False,
        stateless=True,
        telemetry_target=None,
        telemetry_operation=None,
        log_tokens=False,
        thermal_profile="cognitive",
    )
    assert parsed.value == "ok"
    assert create_mock.call_count == 1


def test_path_b_self_correction_then_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = InstructorLLMClient(base_url="http://localhost:1234/v1")
    engine = client._structured_engine
    profile = LlmBackendProfile(
        base_url=client.base_url,
        model=client.model,
        grammar_capability=GrammarCapability.LEGACY_TEXT,
        probed_at=0.0,
    )
    monkeypatch.setattr(engine, "probe_backend", lambda **_: profile)

    calls: list[list[ChatMessage]] = []

    class FakeCompletions:
        def create_with_completion(self, **kwargs: object) -> tuple[object, object]:
            calls.append(list(cast(list[ChatMessage], kwargs["messages"])))
            if len(calls) == 1:
                raise ValidationError.from_exception_data(
                    "Tiny",
                    [{"type": "missing", "loc": ("value",), "input": {}}],
                )
            return GraphInsightsLLMResult(
                ontology_report="ok",
                cleanup_suggestions=[],
            ), MagicMock(usage=None)

    class FakeClient:
        chat = type("Chat", (), {"completions": FakeCompletions()})()

    monkeypatch.setattr(
        "src.agent.llm_client.instructor.from_openai",
        lambda *_a, **_k: FakeClient(),
    )

    messages: list[ChatMessage] = [
        {"role": "system", "content": "s"},
        {"role": "user", "content": "u"},
    ]
    parsed, _ = engine.completion_structured(
        messages=messages,
        response_model=GraphInsightsLLMResult,
        prompt="u",
        started=0.0,
        use_history=False,
        stateless=True,
        telemetry_target=None,
        telemetry_operation=None,
        log_tokens=False,
        thermal_profile="cognitive",
    )
    assert parsed.ontology_report == "ok"
    assert len(calls) == 2
    assert "validation" in calls[1][-1]["content"].lower()


def test_path_b_exhausted_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    client = InstructorLLMClient(base_url="http://localhost:1234/v1")
    engine = client._structured_engine
    profile = LlmBackendProfile(
        base_url=client.base_url,
        model=client.model,
        grammar_capability=GrammarCapability.LEGACY_TEXT,
        probed_at=0.0,
    )
    monkeypatch.setattr(engine, "probe_backend", lambda **_: profile)

    class FakeCompletions:
        def create_with_completion(self, **_kwargs: object) -> tuple[object, object]:
            raise ValidationError.from_exception_data(
                "Tiny",
                [{"type": "missing", "loc": ("value",), "input": {}}],
            )

    class FakeClient:
        chat = type("Chat", (), {"completions": FakeCompletions()})()

    monkeypatch.setattr(
        "src.agent.llm_client.instructor.from_openai",
        lambda *_a, **_k: FakeClient(),
    )
    monkeypatch.setattr(
        client,
        "_raw_json_completion",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("raw fail")),
    )

    messages: list[ChatMessage] = [
        {"role": "system", "content": "s"},
        {"role": "user", "content": "u"},
    ]
    with pytest.raises(StructuredOutputExhaustedError):
        engine.completion_structured(
            messages=messages,
            response_model=GraphInsightsLLMResult,
            prompt="u",
            started=0.0,
            use_history=False,
            stateless=True,
            telemetry_target=None,
            telemetry_operation=None,
            log_tokens=False,
            thermal_profile="cognitive",
        )


def test_compress_history_uses_completion_token_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    client = InstructorLLMClient(base_url="http://localhost:1234/v1")
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content="## Consolidated Epistemic State\n"))]
    response.usage = None
    create_mock = MagicMock(return_value=response)
    monkeypatch.setattr(client._raw_client.chat.completions, "create", create_mock)
    out = client._compress_history_via_llm("compress this history")
    assert "Consolidated" in out
    kwargs = create_mock.call_args.kwargs
    expected = llm_completion_token_limit_kwargs(
        model=client.model,
        limit=DEFAULT_LLM_MAX_COMPRESSION_TOKENS,
    )
    assert expected.items() <= kwargs.items()
