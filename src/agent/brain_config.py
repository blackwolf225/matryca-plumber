"""Environment-driven configuration for Matryca Brain cognitive lint modules."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_bool(key: str, default: bool = False) -> bool:
    raw = os.environ.get(key, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    raw = os.environ.get(key, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass(frozen=True, slots=True)
class BrainLintConfig:
    """Feature flags and thresholds for advanced Brain lint modules."""

    marpa_framework: bool = False
    marpa_strict_bipartite: bool = True
    heal_dangling: bool = False
    dangling_max_words: int = 50
    entity_consolidation: bool = False
    similarity_threshold: float = 0.85
    auto_split: bool = False
    split_block_threshold: int = 15
    property_hygiene: bool = False
    infer_missing_properties: bool = True
    property_rules_path: Path | None = None
    backpropagate_links: bool = False
    semantic_routing: bool = False

    @property
    def any_enabled(self) -> bool:
        return (
            self.marpa_framework
            or self.heal_dangling
            or self.entity_consolidation
            or self.auto_split
            or self.property_hygiene
            or self.backpropagate_links
            or self.semantic_routing
        )


def load_brain_lint_config() -> BrainLintConfig:
    """Load Brain lint settings from environment variables."""
    rules_raw = os.environ.get("MATRYCA_LINT_PROPERTY_RULES", "").strip()
    rules_path = Path(rules_raw).expanduser() if rules_raw else None
    if rules_path is None:
        graph = os.environ.get("LOGSEQ_GRAPH_PATH", "").strip()
        if graph:
            candidate = Path(graph).expanduser() / "matryca-brain-rules.yml"
            if candidate.is_file():
                rules_path = candidate

    return BrainLintConfig(
        marpa_framework=_env_bool("MATRYCA_LINT_MARPA_FRAMEWORK"),
        marpa_strict_bipartite=_env_bool("MATRYCA_LINT_MARPA_STRICT_BIPARTITE", True),
        heal_dangling=_env_bool("MATRYCA_LINT_HEAL_DANGLING"),
        dangling_max_words=_env_int("MATRYCA_LINT_DANGLING_MAX_WORDS", 50),
        entity_consolidation=_env_bool("MATRYCA_LINT_ENTITY_CONSOLIDATION"),
        similarity_threshold=_env_float("MATRYCA_LINT_SIMILARITY_THRESHOLD", 0.85),
        auto_split=_env_bool("MATRYCA_LINT_AUTO_SPLIT"),
        split_block_threshold=_env_int("MATRYCA_LINT_SPLIT_BLOCK_THRESHOLD", 15),
        property_hygiene=_env_bool("MATRYCA_LINT_PROPERTY_HYGIENE"),
        infer_missing_properties=_env_bool("MATRYCA_LINT_INFER_MISSING_PROPERTIES", True),
        property_rules_path=rules_path,
        backpropagate_links=_env_bool("MATRYCA_LINT_BACKPROPAGATE_LINKS"),
        semantic_routing=_env_bool("MATRYCA_LINT_SEMANTIC_ROUTING"),
    )


__all__ = ["BrainLintConfig", "load_brain_lint_config"]
