"""Tests for post-audit security remediations."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from src.cli.ui_auth import reset_ui_token_for_tests
from src.cli.ui_server import _require_loopback_client, app
from src.daemon.git_audit import path_is_sensitive_for_git
from src.graph.path_sandbox import PathTraversalSecurityError, assert_path_within_graph
from src.graph.property_line_edit import _apply_pattern
from src.utils.config_paths import resolve_optional_path_under_allowed_roots
from src.utils.secret_redaction import redact_secrets_in_text
from src.utils.token_logger import TokenLogger


@pytest.fixture(autouse=True)
def ui_auth_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MATRYCA_UI_TOKEN", "test-ui-token")
    reset_ui_token_for_tests()


@pytest.fixture
def graph_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "pages").mkdir()
    monkeypatch.setenv("LOGSEQ_GRAPH_PATH", str(tmp_path))
    return tmp_path


def test_require_loopback_client_rejects_remote_even_when_lan_allowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MATRYCA_UI_ALLOW_LAN", "1")

    class _Client:
        host = "192.168.1.50"

    class _Request:
        client = _Client()

    with pytest.raises(HTTPException) as exc_info:
        _require_loopback_client(_Request())  # type: ignore[arg-type]
    assert exc_info.value.status_code == 403


def test_api_health_is_public(graph_root: Path) -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_symlink_leaf_rejected_in_graph_sandbox(tmp_path: Path) -> None:
    graph = tmp_path / "graph"
    pages = graph / "pages"
    pages.mkdir(parents=True)
    outside = tmp_path / "outside.md"
    outside.write_text("secret\n", encoding="utf-8")
    link = pages / "Link.md"
    link.symlink_to(outside)
    with pytest.raises(PathTraversalSecurityError):
        assert_path_within_graph(link, graph)


def test_edit_property_regex_rejects_catastrophic_pattern() -> None:
    with pytest.raises(ValueError, match="catastrophic"):
        _apply_pattern(
            "text",
            r"(.+)+b",
            "x",
            use_regex=True,
            replace_all=False,
            case_sensitive=True,
        )


def test_redact_secrets_in_text_masks_common_shapes() -> None:
    blob = "Bearer abcdefghijklmnopqrstuvwxyz sk-abcdefghijklmnopqrstuvwxyz1234567890"
    redacted = redact_secrets_in_text(blob)
    assert "sk-" not in redacted
    assert "Bearer [REDACTED]" in redacted


def test_redact_secrets_in_text_masks_anthropic_key() -> None:
    key = "sk-ant-api03-abcdefghijklmnopqrstuvwxyz1234567890"
    redacted = redact_secrets_in_text(f"anthropic: {key}")
    assert key not in redacted
    assert "[REDACTED_API_KEY]" in redacted
    assert redacted.startswith("anthropic: ")


def test_token_logger_redacts_prompts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MATRYCA_PLUMBER_LOG_REDACT_SECRETS", "true")
    log_path = tmp_path / "ops.log"
    logger = TokenLogger(log_path=log_path)
    logger.log_turn(
        target_file="pages/Test.md",
        operation="Concept Indexing",
        prompt_tokens=1,
        completion_tokens=1,
        prompt="key sk-abcdefghijklmnopqrstuvwxyz1234567890",
        response="ok",
        latency_seconds=0.1,
    )
    line = log_path.read_text(encoding="utf-8")
    assert "sk-" not in line


def test_property_rules_path_must_be_under_allowed_roots() -> None:
    assert resolve_optional_path_under_allowed_roots("/etc/passwd") is None


def test_git_sensitive_path_detection() -> None:
    assert path_is_sensitive_for_git(".env")
    assert not path_is_sensitive_for_git("pages/Note.md")


def test_graph_path_for_config_rejects_outside_allowed_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.graph.graph_path_validate import validate_logseq_graph_path_for_config
    from src.utils import config_paths

    allowed = tmp_path / "allowed"
    (allowed / "pages").mkdir(parents=True)
    outside = tmp_path / "outside"
    (outside / "pages").mkdir(parents=True)
    monkeypatch.setattr(
        config_paths,
        "graph_config_allowed_roots",
        lambda: [allowed.resolve()],
    )

    with pytest.raises(ValueError, match="LOGSEQ_GRAPH_PATH must lie under"):
        validate_logseq_graph_path_for_config(str(outside))


def test_mcp_tool_guard_hides_oserror_paths_when_debug_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.agent.mcp_tool_guard import format_tool_error

    monkeypatch.delenv("MATRYCA_DEBUG", raising=False)
    payload = format_tool_error(
        OSError("/secret/path/denied"),
        as_text=False,
    )
    assert isinstance(payload, dict)
    assert "/secret/path" not in str(payload.get("error", ""))
