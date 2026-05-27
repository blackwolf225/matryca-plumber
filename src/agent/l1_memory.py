"""Fast L1 memory: small Markdown files loaded every session (llm-wiki L1 layer)."""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

from ..config import MatrycaWikiConfig
from ..utils.env_placeholders import is_template_env_path
from .llm_context_payload import cap_llm_payload_chars

# Guardrails so agents cannot accidentally load huge trees into context.
_MAX_FILES = 32
_MAX_BYTES_PER_FILE = 64 * 1024
_MAX_BYTES_TOTAL = 256 * 1024
_L1_SKIP_FILENAMES = frozenset({"readme.md"})


def _expand(path: str) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def _l1_markdown_files_in_dir(directory: Path) -> list[Path]:
    """Return sorted ``*.md`` in ``directory``, excluding bootstrap ``README.md``."""
    files = [
        path
        for path in directory.glob("*.md")
        if path.is_file() and path.name.lower() not in _L1_SKIP_FILENAMES
    ]
    return sorted(files)[:_MAX_FILES]


def _l1_path_under_allowed_root(path: Path) -> bool:
    """Return whether ``path`` resolves under the user home or system temp directory."""
    resolved = path.expanduser().resolve(strict=False)
    for root in (Path.home().resolve(), Path(tempfile.gettempdir()).resolve()):
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _is_allowed_l1_path(path: Path) -> bool:
    """Restrict L1 memory reads to allowed roots and existing paths."""
    return _l1_path_under_allowed_root(path) and path.exists()


def _effective_l1_path_override(raw: str | None) -> str:
    """Return ``MATRYCA_L1_PATH`` (or explicit override) ignoring ``.env.example`` templates."""
    if raw is None:
        value = os.environ.get("MATRYCA_L1_PATH", "").strip()
    else:
        value = raw.strip()
    if is_template_env_path(value):
        return ""
    return value


def _effective_memory_path_override(raw: str | None) -> str:
    if raw is None:
        return ""
    stripped = raw.strip()
    if is_template_env_path(stripped):
        return ""
    return stripped


def default_matryca_l1_directory_for_graph(graph_root: Path) -> Path:
    """Return the default sibling ``matryca-l1`` directory for a Logseq graph root."""
    return graph_root.expanduser().resolve(strict=False).parent / "matryca-l1"


_L1_README = """# Matryca L1 memory

Small Markdown files in this folder are loaded first each session (deploy rules, identity, gotchas).

- Default location is **next to** your Logseq vault (`<parent-of-vault>/matryca-l1/`), not inside `pages/`,
  so session rules stay outside the wiki index (L2). To store L1 inside the vault, set `MATRYCA_L1_PATH`
  to `<vault>/matryca-l1` or `memory_path` in `matryca-wiki.yml`.
- Add one or more `*.md` files here (`README.md` is documentation only and is not loaded into context).
- Keep secrets out of L1; store pointers only. Deep wiki content belongs in the Logseq graph (L2).
- See `SYSTEM_PROMPT.md` in the Matryca Plumber repo for L1 vs L2 routing.
"""

_L1_STARTER = """# Session rules (L1)

- Replace this stub with your deploy rules, identity, and operational gotchas.
- Never store credentials here; reference secret locations only.
"""


def resolve_matryca_l1_directory(
    *,
    matryca_l1_path: str | None = None,
    logseq_graph_path: str | None = None,
    memory_path_from_yaml: str | None = None,
) -> Path | None:
    """Resolve the L1 directory to provision (``None`` when using a single ``.md`` file)."""
    l1_raw = _effective_l1_path_override(matryca_l1_path)
    if not l1_raw and memory_path_from_yaml:
        l1_raw = _effective_memory_path_override(memory_path_from_yaml)
    if l1_raw:
        p = _expand(l1_raw)
        if not _l1_path_under_allowed_root(p):
            return None
        if p.is_file():
            return None
        return p

    graph_raw = (
        logseq_graph_path
        if logseq_graph_path is not None
        else os.environ.get("LOGSEQ_GRAPH_PATH", "")
    ).strip()
    if graph_raw and not is_template_env_path(graph_raw):
        return default_matryca_l1_directory_for_graph(_expand(graph_raw))
    return None


def ensure_matryca_l1_dir(
    *,
    matryca_l1_path: str | None = None,
    logseq_graph_path: str | None = None,
    memory_path_from_yaml: str | None = None,
) -> Path | None:
    """Create the resolved L1 directory and starter files when missing.

    Returns:
        The directory path when created or already present under allowed roots, else ``None``.
    """
    target = resolve_matryca_l1_directory(
        matryca_l1_path=matryca_l1_path,
        logseq_graph_path=logseq_graph_path,
        memory_path_from_yaml=memory_path_from_yaml,
    )
    if target is None or not _l1_path_under_allowed_root(target):
        return None

    target.mkdir(parents=True, exist_ok=True)
    readme = target / "README.md"
    if not readme.is_file():
        readme.write_text(_L1_README, encoding="utf-8")
    content_mds = [p for p in target.glob("*.md") if p.name.lower() != "readme.md"]
    if not content_mds:
        starter = target / "session-rules.md"
        if not starter.is_file():
            starter.write_text(_L1_STARTER, encoding="utf-8")
    return target


def collect_l1_markdown_paths(
    *,
    matryca_l1_path: str | None = None,
    logseq_graph_path: str | None = None,
    memory_path_from_yaml: str | None = None,
) -> list[Path]:
    """Resolve which Markdown files constitute L1 for this session.

    Resolution order:

    1. ``MATRYCA_L1_PATH`` — if it points to a ``.md`` file, that file alone; if a
       directory, all ``*.md`` in that directory except ``README.md`` (non-recursive).
    2. Else ``memory_path_from_yaml`` (from ``matryca-wiki.yml``) when non-empty.
    3. Else ``<parent of LOGSEQ_GRAPH_PATH>/matryca-l1/*.md`` when that directory
       exists.

    Args:
        matryca_l1_path: Raw ``MATRYCA_L1_PATH`` env value (optional).
        logseq_graph_path: Raw ``LOGSEQ_GRAPH_PATH`` env value (optional).
        memory_path_from_yaml: ``memory_path`` from :class:`~src.config.MatrycaWikiConfig`.

    Returns:
        Ordered list of files to read (may be empty).
    """
    l1_raw = _effective_l1_path_override(matryca_l1_path)
    if not l1_raw and memory_path_from_yaml:
        l1_raw = _effective_memory_path_override(memory_path_from_yaml)
    if l1_raw:
        p = _expand(l1_raw)
        if not _is_allowed_l1_path(p):
            return []
        if p.is_file():
            return [p] if p.suffix.lower() == ".md" else []
        if p.is_dir():
            return _l1_markdown_files_in_dir(p)

    graph_raw = (
        logseq_graph_path
        if logseq_graph_path is not None
        else os.environ.get("LOGSEQ_GRAPH_PATH", "")
    ).strip()
    if graph_raw:
        fallback = _expand(graph_raw).parent / "matryca-l1"
        if _is_allowed_l1_path(fallback) and fallback.is_dir():
            return _l1_markdown_files_in_dir(fallback)

    return []


def read_l1_memory_text(
    paths: list[Path],
    *,
    max_files: int = _MAX_FILES,
    max_bytes_per_file: int = _MAX_BYTES_PER_FILE,
    max_bytes_total: int = _MAX_BYTES_TOTAL,
) -> tuple[list[str], str]:
    """Read UTF-8 Markdown from ``paths`` with size limits.

    Args:
        paths: Files to read (typically from :func:`collect_l1_markdown_paths`).
        max_files: Maximum number of files to read from ``paths``.
        max_bytes_per_file: Per-file byte cap (excess truncated with a notice).
        max_bytes_total: Total byte budget across all files.

    Returns:
        Tuple of (relative path labels for files actually read, concatenated Markdown
        body for the agent).
    """
    labels: list[str] = []
    chunks: list[str] = []
    total = 0

    for path in paths[:max_files]:
        if not path.is_file():
            continue
        try:
            raw = path.read_bytes()
        except OSError:
            chunks.append(f"<!-- skipped (unreadable): {path} -->\n")
            continue

        truncated = False
        if len(raw) > max_bytes_per_file:
            raw = raw[:max_bytes_per_file]
            truncated = True

        if total + len(raw) > max_bytes_total:
            remaining = max_bytes_total - total
            if remaining <= 0:
                chunks.append("\n\n<!-- L1 total size cap reached; further files omitted. -->\n")
                break
            raw = raw[:remaining]
            truncated = True

        text = raw.decode("utf-8", errors="replace")
        labels.append(path.name)
        total += len(raw)
        notice = " _(truncated to size limit)_" if truncated else ""
        chunks.append(f"## L1: `{path.name}`{notice}\n\n{text.rstrip()}\n")

    if not labels:
        return [], ""

    header = f"# L1 memory (fast context)\n\n**Files loaded:** {', '.join(labels)}\n\n---\n\n"
    return labels, cap_llm_payload_chars(header + "\n".join(chunks).rstrip() + "\n")


def read_l1_memory_from_env(wiki_config: MatrycaWikiConfig | None = None) -> tuple[list[str], str]:
    """Load L1 using environment plus optional :class:`~src.config.MatrycaWikiConfig`."""
    mem_yaml = wiki_config.memory_path if wiki_config else None
    paths = collect_l1_markdown_paths(memory_path_from_yaml=mem_yaml)
    return read_l1_memory_text(paths)


async def read_l1_memory_async(
    wiki_config: MatrycaWikiConfig | None = None,
) -> tuple[list[str], str]:
    """Async wrapper that offloads disk reads to a worker thread."""
    return await asyncio.to_thread(read_l1_memory_from_env, wiki_config)


__all__ = [
    "collect_l1_markdown_paths",
    "default_matryca_l1_directory_for_graph",
    "ensure_matryca_l1_dir",
    "read_l1_memory_async",
    "read_l1_memory_from_env",
    "read_l1_memory_text",
    "resolve_matryca_l1_directory",
]
