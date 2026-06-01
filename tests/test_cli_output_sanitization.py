"""Tests for CLI stdout sanitization (in-place secret masking)."""

from __future__ import annotations

import src.cli as cli_module
from src.utils.secret_redaction import redact_secrets_in_text

_redact = cli_module._redact_text_if_sensitive
_sanitize = cli_module._sanitize_for_output


def test_redact_preserves_normal_text() -> None:
    text = "Found 3 pages under pages/Domain/Note.md with score 0.92"
    assert _redact(text) == text
    assert redact_secrets_in_text(text) == text


def test_redact_masks_openai_key_in_sentence() -> None:
    key = "sk-abcdefghijklmnopqrstuvwxyz1234567890"
    text = f"Config uses key {key} for embeddings."
    redacted = _redact(text)
    assert key not in redacted
    assert "[REDACTED_API_KEY]" in redacted
    assert "Config uses key" in redacted
    assert "for embeddings." in redacted


def test_redact_masks_anthropic_key_in_sentence() -> None:
    key = "sk-ant-api03-abcdefghijklmnopqrstuvwxyz1234567890"
    text = f"Provider key: {key} (rotate quarterly)"
    redacted = _redact(text)
    assert key not in redacted
    assert "[REDACTED_API_KEY]" in redacted
    assert "Provider key:" in redacted
    assert "(rotate quarterly)" in redacted


def test_redact_masks_bearer_token_in_sentence() -> None:
    token = "Bearer abcdefghijklmnopqrstuvwxyz1234567890"
    text = f"Authorization header was {token} last sync."
    redacted = _redact(text)
    assert "Bearer abcdefghijklmnopqrstuvwxyz" not in redacted
    assert "Bearer [REDACTED]" in redacted
    assert "Authorization header was" in redacted


def test_sanitize_for_output_nested_dict() -> None:
    payload = {
        "status": "ok",
        "detail": "key sk-abcdefghijklmnopqrstuvwxyz1234567890 in env",
        "nested": {"token": "sk-ant-api03-abcdefghijklmnopqrstuvwxyz1234567890"},
    }
    safe = _sanitize(payload)
    assert safe["status"] == "ok"
    assert "sk-" not in str(safe["detail"])
    assert "[REDACTED_API_KEY]" in safe["detail"]
    assert "sk-ant" not in str(safe["nested"]["token"])
    assert safe["nested"]["token"] == "[REDACTED_API_KEY]"


def test_sanitize_for_output_list_of_strings() -> None:
    items = ["line one", "Bearer abcdefghijklmnopqrstuvwxyz1234567890", "line three"]
    safe = _sanitize(items)
    assert safe[0] == "line one"
    assert safe[2] == "line three"
    assert "Bearer [REDACTED]" in safe[1]


def test_redact_masks_logseq_credential_property() -> None:
    text = "token:: my-secret-value-here"
    redacted = _redact(text)
    assert "my-secret-value-here" not in redacted
    assert "[REDACTED_CREDENTIAL_PROPERTY]" in redacted
