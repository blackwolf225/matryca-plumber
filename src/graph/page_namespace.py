"""Page title namespace heuristics (MARPA path segments)."""

from __future__ import annotations


def detect_marpa_namespace(page_title: str) -> str | None:
    """Return namespace segment from ``Area/Topic`` or ``Area___Topic`` titles."""
    if "/" in page_title:
        return page_title.split("/", 1)[0].casefold()
    if "___" in page_title:
        return page_title.split("___", 1)[0].casefold()
    return None


__all__ = ["detect_marpa_namespace"]
