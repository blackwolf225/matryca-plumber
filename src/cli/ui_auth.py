"""Local auth token for the Matryca Plumber Sovereign UI API."""

from __future__ import annotations

import os
import secrets

_resolved_token: str | None = None


def resolve_ui_token() -> str:
    """Return the active UI bearer token (from env or generated once per process)."""
    global _resolved_token
    if _resolved_token is not None:
        return _resolved_token
    env = os.environ.get("MATRYCA_UI_TOKEN", "").strip()
    _resolved_token = env if env else secrets.token_urlsafe(32)
    return _resolved_token


def ui_token_is_ephemeral() -> bool:
    """True when the bearer token was auto-generated (not set in the environment)."""
    return not os.environ.get("MATRYCA_UI_TOKEN", "").strip()


def warn_if_ephemeral_ui_token() -> None:
    """Log operator guidance when the UI token is generated per process."""
    if not ui_token_is_ephemeral():
        return
    from loguru import logger

    logger.warning(
        "SECURITY: MATRYCA_UI_TOKEN is unset — a random bearer token was "
        "generated for this process. "
        "Any local process on loopback can obtain it via GET /api/auth/session and call protected "
        "endpoints (including /api/config with LLM credentials). "
        "Set MATRYCA_UI_TOKEN to a long random value, or enable "
        "MATRYCA_UI_REQUIRE_EXPLICIT_TOKEN=true. "
        "See SECURITY.md for shared-host guidance."
    )


def require_explicit_ui_token_if_configured() -> None:
    """Refuse UI startup when ``MATRYCA_UI_REQUIRE_EXPLICIT_TOKEN`` is enabled without a token."""
    raw = os.environ.get("MATRYCA_UI_REQUIRE_EXPLICIT_TOKEN", "").strip().lower()
    if raw not in {"1", "true", "yes", "on"}:
        return
    if os.environ.get("MATRYCA_UI_TOKEN", "").strip():
        return
    msg = (
        "MATRYCA_UI_REQUIRE_EXPLICIT_TOKEN is enabled but MATRYCA_UI_TOKEN is empty. "
        "Set MATRYCA_UI_TOKEN before starting the Sovereign UI."
    )
    raise ValueError(msg)


def verify_ui_token(provided: str | None) -> bool:
    """Constant-time comparison against the active UI token."""
    if not provided or not provided.strip():
        return False
    return secrets.compare_digest(provided.strip(), resolve_ui_token())


def reset_ui_token_for_tests() -> None:
    """Clear cached token (tests only)."""
    global _resolved_token
    _resolved_token = None


def require_explicit_ui_token_for_lan() -> None:
    """Refuse LAN exposure unless the operator set a non-empty ``MATRYCA_UI_TOKEN``."""
    allow_lan = os.environ.get("MATRYCA_UI_ALLOW_LAN", "").strip().lower()
    if allow_lan not in {"1", "true", "yes", "on"}:
        return
    if os.environ.get("MATRYCA_UI_TOKEN", "").strip():
        return
    msg = (
        "MATRYCA_UI_TOKEN must be set to a strong random value when MATRYCA_UI_ALLOW_LAN is enabled"
    )
    raise ValueError(msg)


__all__ = [
    "require_explicit_ui_token_for_lan",
    "require_explicit_ui_token_if_configured",
    "reset_ui_token_for_tests",
    "resolve_ui_token",
    "ui_token_is_ephemeral",
    "verify_ui_token",
    "warn_if_ephemeral_ui_token",
]
