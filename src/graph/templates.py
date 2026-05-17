"""Read Logseq ``templates/*.md`` for agent-side template hydration (Templater-style)."""

from __future__ import annotations

from pathlib import Path


def _safe_templates_dir(graph_root: Path, subdir: str) -> Path:
    root = graph_root.expanduser().resolve(strict=False)
    td = (root / subdir.strip().replace("\\", "/").strip("/")).resolve()
    try:
        td.relative_to(root.resolve())
    except ValueError as exc:
        msg = "template_dir_escapes_graph"
        raise ValueError(msg) from exc
    return td


def list_logseq_templates(graph_root: str | Path, *, subdir: str = "templates") -> list[str]:
    """Basenames ``*.md`` under ``<graph>/<subdir>/``."""
    td = _safe_templates_dir(Path(graph_root), subdir)
    if not td.is_dir():
        return []
    return sorted(p.name for p in sorted(td.glob("*.md")) if p.is_file())


def read_logseq_template(
    graph_root: str | Path,
    template_name: str,
    *,
    subdir: str = "templates",
) -> tuple[str, str]:
    """Return ``(relative_path, utf8_text)`` for one template file.

    Raises:
        FileNotFoundError: When the template is missing.
        ValueError: When ``template_name`` is not a plain basename.
    """
    name = template_name.strip()
    if not name or "/" in name or "\\" in name or name.startswith("."):
        msg = "template_name must be a plain filename (e.g. daily.md)"
        raise ValueError(msg)
    if not name.endswith(".md"):
        name = f"{name}.md"

    td = _safe_templates_dir(Path(graph_root), subdir)
    path = (td / name).resolve()
    try:
        path.relative_to(td)
    except ValueError as exc:
        msg = "template_path_invalid"
        raise ValueError(msg) from exc

    if not path.is_file():
        msg = f"template not found: {path}"
        raise FileNotFoundError(msg)

    text = path.read_text(encoding="utf-8", errors="replace")
    rel = path.relative_to(Path(graph_root).expanduser().resolve(strict=False))
    return (rel.as_posix(), text)


__all__ = ["list_logseq_templates", "read_logseq_template"]
