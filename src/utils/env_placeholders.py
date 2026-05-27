"""Detect template placeholder paths copied from ``.env.example``."""

from __future__ import annotations

_TEMPLATE_FRAGMENTS: tuple[str, ...] = (
    "/absolute/path/to/",
    "/path/to/your/",
)

_EXACT_TEMPLATE_PATHS: frozenset[str] = frozenset(
    {
        "/absolute/path/to/matryca-l1",
        "/absolute/path/to/your/logseq/graph",
    }
)


def normalize_env_path_value(value: str) -> str:
    """Strip whitespace and optional surrounding quotes from a dotenv path value."""
    return value.strip().strip('"').strip("'")


def is_template_env_path(value: str | None) -> bool:
    """Return whether ``value`` is an unfilled example path from ``.env.example``."""
    if value is None:
        return False
    normalized = normalize_env_path_value(value)
    if not normalized:
        return False
    lower = normalized.lower()
    if lower in _EXACT_TEMPLATE_PATHS:
        return True
    return any(fragment in lower for fragment in _TEMPLATE_FRAGMENTS)


__all__ = ["is_template_env_path", "normalize_env_path_value"]
