"""Tests for shared LLM inference URL SSRF policy."""

from __future__ import annotations

import pytest
from src.agent.plumber_config import resolve_validated_llm_base_url
from src.utils.llm_url_policy import UnsafeLlmProxyUrlError, validate_llm_proxy_url


def test_validate_llm_proxy_url_allows_localhost() -> None:
    url = validate_llm_proxy_url(
        "http://localhost:1234", configured_base_url="http://localhost:1234"
    )
    assert url == "http://localhost:1234/v1"


def test_validate_llm_proxy_url_rejects_metadata_ip() -> None:
    with pytest.raises(UnsafeLlmProxyUrlError, match="not allowed"):
        validate_llm_proxy_url(
            "http://169.254.169.254/latest/meta-data/",
            configured_base_url="http://localhost:1234/v1",
        )


def test_validate_llm_proxy_url_rejects_non_http_scheme() -> None:
    with pytest.raises(UnsafeLlmProxyUrlError, match="http or https"):
        validate_llm_proxy_url("file:///etc/passwd", configured_base_url="http://localhost:1234/v1")


def test_resolve_validated_llm_base_url_rejects_env_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "http://169.254.169.254/v1")
    monkeypatch.delenv("MATRYCA_LM_BASE_URL", raising=False)
    with pytest.raises(UnsafeLlmProxyUrlError):
        resolve_validated_llm_base_url()
