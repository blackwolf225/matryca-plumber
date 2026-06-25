"""Structural asserts for Tier-1 daemon system prompts (living tests).

These tests capture the pre-refactor baseline and MUST be extended when new
prompt invariants ship (e.g. semantic_lint rule (6) dead zones).

Token budgets apply ONLY to ``builder.build()`` / system prompt strings —
never to cache-aligned user blocks that include page content.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path

import pytest
from src.agent.bootstrap.prompts import build_harvest_system_prompt
from src.agent.compression.prompts import build_compression_system_prompt
from src.agent.plumber_modules.llm_prompts import (
    build_contextual_seed_system_prompt,
    build_entity_overlap_system_prompt,
    build_tag_properties_system_prompt,
)
from src.agent.plumber_modules.marpa.prompts import build_marpa_classify_system_prompt
from src.agent.semantic_lint.prompts import build_semantic_lint_system_prompt
from src.graph.insights.prompts import build_insights_system_prompt

_CROSS_LINGUAL_TAIL = "[CRITICAL LANGUAGE CONSTRAINT]"

PROMPT_BUDGETS: dict[str, int] = {
    "semantic_lint": 2500,
    "marpa_classify": 2000,
    "contextual_seed": 2000,
    "entity_overlap": 2000,
    "tag_properties": 2000,
    "harvest": 2000,
    "compression": 2000,
    "insights": 2500,
}

TIER_1A_BUILDERS: dict[str, Callable[[], str]] = {
    "semantic_lint": build_semantic_lint_system_prompt,
    "marpa_classify": build_marpa_classify_system_prompt,
    "contextual_seed": build_contextual_seed_system_prompt,
    "entity_overlap": build_entity_overlap_system_prompt,
    "tag_properties": build_tag_properties_system_prompt,
    "harvest": build_harvest_system_prompt,
    "insights": build_insights_system_prompt,
}

TIER_1B_BUILDERS: dict[str, Callable[[], str]] = {
    "compression": build_compression_system_prompt,
}

REQUIRED_SUBSTRINGS: dict[str, list[str]] = {
    "semantic_lint": [
        "block_uuid",
        "id::",
        "(5) if unsure, omit the correction",
        "(6) never propose edits inside fenced code",
        "[INVARIANTS]",
        "[OUTPUT]",
        _CROSS_LINGUAL_TAIL,
    ],
    "marpa_classify": ["Return JSON only", "[INVARIANTS]", _CROSS_LINGUAL_TAIL],
    "contextual_seed": ["Return JSON only", "[INVARIANTS]", _CROSS_LINGUAL_TAIL],
    "entity_overlap": ["[INVARIANTS]", _CROSS_LINGUAL_TAIL],
    "tag_properties": ["Return JSON", "[INVARIANTS]", _CROSS_LINGUAL_TAIL],
    "harvest": ["Return JSON only", "[INVARIANTS]", _CROSS_LINGUAL_TAIL],
    "insights": ["Return JSON only", "GraphInsightsLLMResult", _CROSS_LINGUAL_TAIL],
    "compression": ["[GOAL]", _CROSS_LINGUAL_TAIL],
}

FORBIDDEN_SUBSTRINGS: dict[str, list[str]] = {
    "compression": ["return json only"],
}

GLOBAL_FORBIDDEN = ("english only", "write in english")

_PROMPT_HASH_FILE = Path(__file__).resolve().parent / "prompt_hash_snapshots.json"
_ALL_BUILDERS: dict[str, Callable[[], str]] = {**TIER_1A_BUILDERS, **TIER_1B_BUILDERS}


def _load_known_prompt_hashes() -> dict[str, str]:
    payload = json.loads(_PROMPT_HASH_FILE.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = f"{_PROMPT_HASH_FILE.name} must be a JSON object"
        raise TypeError(msg)
    return {str(k): str(v) for k, v in payload.items()}


def _sha256_prompt(builder: Callable[[], str]) -> str:
    return hashlib.sha256(builder().encode()).hexdigest()


def update_prompt_hash_snapshots() -> None:
    """Rewrite tests/prompt_hash_snapshots.json from current builders."""
    known = {name: _sha256_prompt(builder) for name, builder in _ALL_BUILDERS.items()}
    _PROMPT_HASH_FILE.write_text(
        json.dumps(known, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


@pytest.mark.parametrize("name,builder", list(TIER_1A_BUILDERS.items()))
def test_tier1a_system_prompt_budget(name: str, builder: Callable[[], str]) -> None:
    prompt = builder()
    assert prompt.strip()
    assert len(prompt) < PROMPT_BUDGETS[name], (
        f"{name} system prompt length {len(prompt)} exceeds budget {PROMPT_BUDGETS[name]}"
    )


@pytest.mark.parametrize("name,builder", list(TIER_1B_BUILDERS.items()))
def test_tier1b_system_prompt_budget(name: str, builder: Callable[[], str]) -> None:
    prompt = builder()
    assert prompt.strip()
    assert len(prompt) < PROMPT_BUDGETS[name]


@pytest.mark.parametrize("name,builder", list(TIER_1A_BUILDERS.items()))
def test_tier1a_required_substrings(name: str, builder: Callable[[], str]) -> None:
    prompt = builder()
    lowered = prompt.lower()
    for fragment in REQUIRED_SUBSTRINGS[name]:
        assert fragment.lower() in lowered, f"{name}: missing required substring {fragment!r}"


@pytest.mark.parametrize("name,builder", list({**TIER_1A_BUILDERS, **TIER_1B_BUILDERS}.items()))
def test_no_english_only_hardcoding(name: str, builder: Callable[[], str]) -> None:
    lowered = builder().lower()
    for forbidden in GLOBAL_FORBIDDEN:
        assert forbidden not in lowered, f"{name}: forbidden hardcoded language rule {forbidden!r}"


@pytest.mark.parametrize("name,builder", list(TIER_1B_BUILDERS.items()))
def test_tier1b_no_return_json_only(name: str, builder: Callable[[], str]) -> None:
    lowered = builder().lower()
    for forbidden in FORBIDDEN_SUBSTRINGS.get(name, ()):
        assert forbidden not in lowered, f"{name}: Tier-1B must not contain {forbidden!r}"


def test_semantic_lint_numbered_invariants_ordered() -> None:
    prompt = build_semantic_lint_system_prompt()
    pos_1 = prompt.find("(1) block_uuid")
    pos_6 = prompt.find("(6) never propose edits inside fenced code")
    pos_output = prompt.find("[OUTPUT]")
    tail = prompt.find(_CROSS_LINGUAL_TAIL)
    assert pos_1 != -1 and pos_6 != -1 and pos_output != -1 and tail != -1
    assert pos_1 < pos_6 < pos_output < tail


def test_prompt_hash_stability() -> None:
    known = _load_known_prompt_hashes()
    assert set(known) == set(_ALL_BUILDERS), "prompt_hash_snapshots.json keys must match builders"
    for name, builder in _ALL_BUILDERS.items():
        actual = _sha256_prompt(builder)
        expected = known[name]
        assert actual == expected, (
            f"{name}: hash changed — update with: "
            "pytest tests/test_daemon_prompts.py --update-prompt-hashes"
        )


def test_domain_builders_do_not_import_prompt_constraints_directly() -> None:
    """Enforce Dependency Rule: domain prompt modules import only prompts.core."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "src"
    domain_dirs = (
        root / "agent" / "semantic_lint",
        root / "agent" / "bootstrap",
        root / "agent" / "compression",
        root / "agent" / "plumber_modules" / "marpa",
        root / "agent" / "plumber_modules" / "llm_prompts",
        root / "graph" / "insights",
    )
    forbidden = "prompt_constraints"
    for directory in domain_dirs:
        for path in directory.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            assert forbidden not in text, f"{path.relative_to(root)} must not import {forbidden}"
