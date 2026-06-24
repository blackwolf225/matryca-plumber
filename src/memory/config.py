"""Environment-driven configuration for the biological memory graph (Epic #99)."""

from __future__ import annotations

from ..utils.env_parse import env_bool


def memory_graph_enabled() -> bool:
    """Return whether the Nacre-inspired memory graph layer is active."""
    return env_bool("MATRYCA_MEMORY_GRAPH_ENABLED", default=False)


__all__ = ["memory_graph_enabled"]
