"""Ensure Matryca runtime directories and config exist before graph processing.

Provisioned on every Matryca Plumber startup (MCP lifespan, daemon, UI, CLI):

- **Logs** — parent dirs for ``MATRYCA_PLUMBER_LOG_PATH`` and ``MATRYCA_LOGURU_LOG_PATH``
  (default: repo ``logs/``).
- **L1** — ``<parent-of-vault>/matryca-l1/`` with ``README.md`` + ``session-rules.md`` when empty.
- **Graph** — ``.matryca_semantic_cache/``, ``templates/`` (or ``templates_subdir`` from wiki YAML).
- **Wiki config** — ``matryca-wiki.yml`` seeded from ``matryca-wiki.example.yml`` when missing.

Created lazily on first use (not at bootstrap): ``.matryca_daemon_state.json``,
``.matryca_xray_state.json``, daemon PID/lock files, catalog JSON bodies.
Repo ``.env`` is operator-managed (``cp .env.example .env``).
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from loguru import logger

from ..agent.l1_memory import ensure_matryca_l1_dir
from ..config import MatrycaWikiConfig, load_matryca_wiki_config
from .config_paths import ensure_plumber_log_directories

_REPO_ROOT = Path(__file__).resolve().parents[2]
_WIKI_EXAMPLE = _REPO_ROOT / "matryca-wiki.example.yml"
_SEMANTIC_CACHE_DIR = ".matryca_semantic_cache"


def ensure_graph_runtime_directories(
    graph_root: Path,
    *,
    templates_subdir: str = "templates",
) -> None:
    """Create graph-local Matryca working directories (cache, templates)."""
    root = graph_root.expanduser().resolve(strict=False)
    (root / _SEMANTIC_CACHE_DIR).mkdir(parents=True, exist_ok=True)
    subdir = (templates_subdir or "templates").strip().strip("/\\")
    if subdir:
        (root / subdir).mkdir(parents=True, exist_ok=True)


def _patch_memory_path_in_wiki_yaml(text: str, l1_dir: Path) -> str:
    escaped = str(l1_dir).replace("\\", "\\\\")
    if re.search(r"^memory_path:\s*", text, flags=re.MULTILINE):
        return re.sub(
            r"^memory_path:\s*.*$",
            f"memory_path: {escaped}",
            text,
            count=1,
            flags=re.MULTILINE,
        )
    return f"memory_path: {escaped}\n\n{text}"


def ensure_matryca_wiki_config_file(
    graph_root: Path,
    *,
    l1_dir: Path | None = None,
) -> Path | None:
    """Seed ``matryca-wiki.yml`` from the repo example when missing under the graph root."""
    root = graph_root.expanduser().resolve(strict=False)
    target = root / "matryca-wiki.yml"
    if target.is_file():
        return target
    if not _WIKI_EXAMPLE.is_file():
        return None
    text = _WIKI_EXAMPLE.read_text(encoding="utf-8")
    if l1_dir is not None:
        text = _patch_memory_path_in_wiki_yaml(text, l1_dir)
    target.write_text(text, encoding="utf-8")
    logger.bind(path=str(target)).info("Created matryca-wiki.yml from matryca-wiki.example.yml")
    return target


def prepare_matryca_runtime(
    *,
    graph_root: Path | None = None,
    wiki_config: MatrycaWikiConfig | None = None,
) -> None:
    """Provision logs, L1 memory, graph cache dirs, and optional wiki config before work."""
    ensure_plumber_log_directories()
    if graph_root is None:
        return

    cfg = wiki_config or MatrycaWikiConfig()
    l1_dir = ensure_matryca_l1_dir(
        logseq_graph_path=str(graph_root),
        memory_path_from_yaml=cfg.memory_path,
    )
    ensure_graph_runtime_directories(graph_root, templates_subdir=cfg.templates_subdir)
    ensure_matryca_wiki_config_file(graph_root, l1_dir=l1_dir)


def try_prepare_matryca_runtime_from_env() -> None:
    """Provision runtime dirs from the current process environment (idempotent)."""
    wiki_config = load_matryca_wiki_config()
    graph_raw = os.environ.get("LOGSEQ_GRAPH_PATH", "").strip()
    if not graph_raw:
        prepare_matryca_runtime(graph_root=None, wiki_config=wiki_config)
        return
    from ..graph.graph_path_validate import validate_logseq_graph_path

    try:
        graph_root = validate_logseq_graph_path(graph_raw)
    except ValueError:
        prepare_matryca_runtime(graph_root=None, wiki_config=wiki_config)
        return
    prepare_matryca_runtime(graph_root=graph_root, wiki_config=wiki_config)


__all__ = [
    "ensure_graph_runtime_directories",
    "ensure_matryca_wiki_config_file",
    "prepare_matryca_runtime",
    "try_prepare_matryca_runtime_from_env",
]
