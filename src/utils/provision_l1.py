"""Onboarding helper: provision sibling ``matryca-l1/`` for a configured Logseq graph."""

from __future__ import annotations

import os
from pathlib import Path

from loguru import logger

from ..agent.l1_memory import default_matryca_l1_directory_for_graph, ensure_matryca_l1_dir
from ..agent.plumber_config import reload_plumber_dotenv, resolve_repo_dotenv_path
from ..config import load_matryca_wiki_config
from .env_placeholders import is_template_env_path
from .runtime_bootstrap import (
    _patch_memory_path_in_wiki_yaml,
    ensure_graph_runtime_directories,
    prepare_matryca_runtime,
)


def clear_matryca_l1_path_placeholder_in_dotenv(*, repo_root: Path | None = None) -> bool:
    """Remove or blank ``MATRYCA_L1_PATH`` in repo ``.env`` when it is still a template.

    Returns:
        ``True`` when the file was modified.
    """
    env_path: Path | None = None
    if repo_root is not None:
        candidate = repo_root / ".env"
        if candidate.is_file():
            env_path = candidate
    elif resolve_repo_dotenv_path() is not None:
        env_path = resolve_repo_dotenv_path()
    if env_path is None or not env_path.is_file():
        return False

    lines = env_path.read_text(encoding="utf-8").splitlines()
    changed = False
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in line:
            new_lines.append(line)
            continue
        key, sep, value = line.partition("=")
        if key.strip() != "MATRYCA_L1_PATH":
            new_lines.append(line)
            continue
        if is_template_env_path(value):
            changed = True
            new_lines.append(
                "# MATRYCA_L1_PATH=  # cleared template; default: <parent-of-vault>/matryca-l1/"
            )
            os.environ.pop("MATRYCA_L1_PATH", None)
            continue
        new_lines.append(line)

    if changed:
        env_path.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")
        reload_plumber_dotenv()
        logger.info("Cleared template MATRYCA_L1_PATH from {}", env_path)
    return changed


def sync_wiki_memory_path_to_l1(graph_root: Path, l1_dir: Path) -> None:
    """Patch ``memory_path`` in an existing ``matryca-wiki.yml`` under the graph root."""
    wiki_path = graph_root / "matryca-wiki.yml"
    if not wiki_path.is_file():
        return
    text = wiki_path.read_text(encoding="utf-8")
    wiki_path.write_text(_patch_memory_path_in_wiki_yaml(text, l1_dir), encoding="utf-8")


def provision_matryca_l1_sibling(*, graph_root: Path, repo_root: Path | None = None) -> Path:
    """Create sibling ``matryca-l1/`` for ``graph_root`` and sync wiki config.

    Raises:
        ValueError: When the directory cannot be created under allowed roots.
    """
    clear_matryca_l1_path_placeholder_in_dotenv(repo_root=repo_root)
    reload_plumber_dotenv()

    wiki_config = load_matryca_wiki_config()

    l1_dir = ensure_matryca_l1_dir(
        matryca_l1_path=None,
        logseq_graph_path=str(graph_root),
        memory_path_from_yaml=None,
    )
    if l1_dir is None:
        planned = default_matryca_l1_directory_for_graph(graph_root)
        raise ValueError(
            f"Could not provision matryca-l1 at {planned} "
            "(path must lie under your home directory or temp)"
        )

    sync_wiki_memory_path_to_l1(graph_root, l1_dir)
    ensure_graph_runtime_directories(graph_root, templates_subdir=wiki_config.templates_subdir)
    prepare_matryca_runtime(
        graph_root=graph_root,
        wiki_config=load_matryca_wiki_config(),
        eager_graph=False,
    )
    return l1_dir


__all__ = [
    "clear_matryca_l1_path_placeholder_in_dotenv",
    "provision_matryca_l1_sibling",
    "sync_wiki_memory_path_to_l1",
]
