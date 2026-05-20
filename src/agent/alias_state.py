"""Persistent session alias registry for stateless CLI / MCP invocations."""

from __future__ import annotations

import json
import re
from pathlib import Path

from logseq_matryca_parser.agent_press import XRAY_STATE_FILENAME, SessionAliasRegistry

from ..graph.markdown_blocks import atomic_write_bytes
from ..graph.page_write_lock import page_rmw_lock

_ALIAS_TARGET_RE = re.compile(r"^\[\s*(\d+)\s*\]$")


def alias_file_path(graph_root: str | Path) -> Path:
    """Hidden X-Ray alias state file at the Logseq graph root."""
    root = Path(graph_root).expanduser().resolve(strict=False)
    state_name = str(XRAY_STATE_FILENAME)
    return root / state_name


def _graph_root_path(graph_root: str | Path) -> Path:
    return Path(graph_root).expanduser().resolve(strict=False)


def load_alias_registry(graph_root: str | Path) -> SessionAliasRegistry:
    """Load alias registry from disk; returns an empty registry when the file is missing."""
    path = alias_file_path(graph_root)
    if not path.is_file():
        return SessionAliasRegistry()
    with page_rmw_lock(path):
        try:
            return SessionAliasRegistry.load_from_disk(path)
        except json.JSONDecodeError as exc:
            msg = f"Corrupt {XRAY_STATE_FILENAME}: {exc}. Re-run xray_page read."
            raise ValueError(msg) from exc
        except UnicodeDecodeError as exc:
            msg = f"Corrupt {XRAY_STATE_FILENAME} (invalid UTF-8): {exc}. Re-run xray_page read."
            raise ValueError(msg) from exc
        except OSError as exc:
            msg = f"Cannot read {path.name}: {exc}"
            raise ValueError(msg) from exc
        except ValueError as exc:
            msg = f"Invalid {XRAY_STATE_FILENAME} schema: {exc}. Re-run xray_page read."
            raise ValueError(msg) from exc


def save_alias_registry(graph_root: str | Path, registry: SessionAliasRegistry) -> Path:
    """Persist ``SessionAliasRegistry`` atomically under an exclusive file lock."""
    path = alias_file_path(graph_root)
    root = _graph_root_path(graph_root)
    payload = {str(alias): block_uuid for alias, block_uuid in registry._alias_to_uuid.items()}  # noqa: SLF001
    data = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    with page_rmw_lock(path):
        atomic_write_bytes(path, data, graph_root=root)
    return path


def resolve_target(graph_root: str | Path, target: str) -> str:
    """Resolve ``[n]`` session aliases to Logseq UUIDs; pass through other targets."""
    raw = target.strip()
    match = _ALIAS_TARGET_RE.fullmatch(raw)
    if not match:
        return target
    alias = int(match.group(1))
    registry = load_alias_registry(graph_root)
    uuid = registry.resolve_alias(alias)
    if uuid is None:
        msg = (
            f"Unknown session alias {raw!r}. Run `read_graph_data` with "
            f'`target_type="xray_page"` on the page first to refresh '
            f"`{XRAY_STATE_FILENAME}`."
        )
        raise ValueError(msg)
    return str(uuid)


def resolve_pipe_target(graph_root: str | Path, target: str) -> str:
    """Resolve aliases in ``Page Title|block-uuid`` (or ``Page Title|[n]``) targets."""
    parts = [segment.strip() for segment in target.split("|", 1)]
    if len(parts) == 2 and parts[0] and parts[1]:
        return f"{parts[0]}|{resolve_target(graph_root, parts[1])}"
    return resolve_target(graph_root, target)


__all__ = [
    "alias_file_path",
    "load_alias_registry",
    "resolve_pipe_target",
    "resolve_target",
    "save_alias_registry",
]
