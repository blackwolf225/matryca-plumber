"""L0 hard-rejection validators for LLM-backed graph writes."""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..global_fence_scanner import compute_page_protected_line_indices

_ID_LINE = re.compile(r"^\s*id::\s*.+\s*$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class SafetyValidationResult:
    ok: bool
    reason: str = ""


def _id_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if _ID_LINE.match(line)]


def reject_id_line_deletion(before: str, after: str) -> SafetyValidationResult:
    """Reject writes that remove any on-disk ``id::`` line."""
    after_ids = set(_id_lines(after))
    for line in _id_lines(before):
        if line not in after_ids:
            return SafetyValidationResult(False, "id_line_deleted")
    return SafetyValidationResult(True)


def reject_protected_zones_modification(before: str, after: str) -> SafetyValidationResult:
    """Reject writes that mutate fenced code, HTML comments, or advanced queries."""
    protected = compute_page_protected_line_indices(before)
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    for idx in protected:
        if idx >= len(before_lines):
            continue
        if idx >= len(after_lines):
            return SafetyValidationResult(False, f"protected_line_removed:{idx}")
        if before_lines[idx] != after_lines[idx]:
            return SafetyValidationResult(False, f"protected_line_modified:{idx}")
    return SafetyValidationResult(True)


def validate_llm_write_diff(before: str, after: str) -> SafetyValidationResult:
    """Run all L0 validators; first failure wins."""
    for validator in (reject_id_line_deletion, reject_protected_zones_modification):
        result = validator(before, after)
        if not result.ok:
            return result
    return SafetyValidationResult(True)


__all__ = [
    "SafetyValidationResult",
    "reject_id_line_deletion",
    "reject_protected_zones_modification",
    "validate_llm_write_diff",
]
