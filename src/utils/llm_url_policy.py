"""SSRF guard for OpenAI-compatible local inference URLs (UI + daemon)."""

from __future__ import annotations

import ipaddress
import socket
import urllib.parse
from typing import NoReturn

_LOCAL_LM_PROXY_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_BLOCKED_SSRF_HOSTS = frozenset(
    {
        "169.254.169.254",
        "metadata.google.internal",
        "metadata.google.internal.",
    },
)


class UnsafeLlmProxyUrlError(ValueError):
    """Raised when an inference base URL fails host/DNS SSRF policy."""


def normalize_lm_proxy_host(host: str) -> str:
    normalized = host.strip().lower()
    if normalized.startswith("[") and normalized.endswith("]"):
        return normalized[1:-1]
    return normalized


def configured_lm_proxy_host(configured_base_url: str) -> str:
    """Return the hostname from the active configured inference base URL."""
    return urllib.parse.urlparse(configured_base_url.strip()).hostname or ""


def _is_safe_lm_proxy_host(host: str, *, configured_host: str) -> bool:
    normalized = normalize_lm_proxy_host(host)
    if normalized in _BLOCKED_SSRF_HOSTS:
        return False
    if normalized in _LOCAL_LM_PROXY_HOSTS:
        return True
    configured = normalize_lm_proxy_host(configured_host)
    return bool(configured) and normalized == configured


def _normalize_inference_ip(
    address: ipaddress.IPv4Address | ipaddress.IPv6Address,
) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        return address.ipv4_mapped
    return address


def _is_blocked_inference_ip(
    address: ipaddress.IPv4Address | ipaddress.IPv6Address,
    *,
    hostname: str,
) -> bool:
    address = _normalize_inference_ip(address)
    if str(address) == "169.254.169.254":
        return True
    if address.is_loopback:
        return normalize_lm_proxy_host(hostname) not in _LOCAL_LM_PROXY_HOSTS
    if (
        address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    ):
        return True
    if isinstance(address, ipaddress.IPv4Address) and address.is_private:
        return normalize_lm_proxy_host(hostname) not in _LOCAL_LM_PROXY_HOSTS
    if isinstance(address, ipaddress.IPv6Address) and address.is_site_local:
        return normalize_lm_proxy_host(hostname) not in _LOCAL_LM_PROXY_HOSTS
    return False


def host_resolves_to_blocked_ip(hostname: str) -> bool:
    """Return whether ``hostname`` resolves to a blocked inference target."""
    normalized = normalize_lm_proxy_host(hostname)
    if normalized in _BLOCKED_SSRF_HOSTS:
        return True
    try:
        literal = ipaddress.ip_address(normalized)
    except ValueError:
        literal = None

    if literal is not None:
        return _is_blocked_inference_ip(literal, hostname=normalized)

    try:
        for info in socket.getaddrinfo(normalized, None, type=socket.SOCK_STREAM):
            sockaddr = info[4]
            if not sockaddr:
                continue
            resolved = ipaddress.ip_address(sockaddr[0])
            if _is_blocked_inference_ip(resolved, hostname=normalized):
                return True
    except OSError:
        return True
    return False


def _reject(reason: str) -> NoReturn:
    raise UnsafeLlmProxyUrlError(reason)


def validate_llm_proxy_url(
    base_url: str,
    *,
    configured_base_url: str | None = None,
) -> str:
    """Validate and return a canonical OpenAI-compatible base URL.

    Args:
        base_url: Candidate ``LLM_BASE_URL`` / LM Studio endpoint.
        configured_base_url: Existing configured base URL used to allow a stable
            non-localhost host (same hostname only). When omitted, only loopback
            hosts and blocked metadata targets are permitted.

    Raises:
        UnsafeLlmProxyUrlError: When the URL is not an allowed inference endpoint.
    """
    from ..agent.plumber_config import resolve_llm_base_url

    parsed = urllib.parse.urlparse(base_url.strip())
    if parsed.scheme not in {"http", "https"}:
        _reject("base_url must use http or https")
    hostname = parsed.hostname
    if not hostname:
        _reject("base_url must include a host")
    configured_host = (
        configured_lm_proxy_host(configured_base_url)
        if configured_base_url
        else ""
    )
    if not _is_safe_lm_proxy_host(hostname, configured_host=configured_host):
        _reject("base_url host is not allowed")
    if host_resolves_to_blocked_ip(hostname):
        _reject("base_url host is not allowed")
    return resolve_llm_base_url(override=base_url)


__all__ = [
    "UnsafeLlmProxyUrlError",
    "configured_lm_proxy_host",
    "host_resolves_to_blocked_ip",
    "normalize_lm_proxy_host",
    "validate_llm_proxy_url",
]
