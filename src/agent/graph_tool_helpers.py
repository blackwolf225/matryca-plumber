"""Shared helpers and literal types for MCP mega-tools and the agent CLI."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Literal, cast

from ..graph.markdown_blocks import locate_block_by_uuid
from ..graph.path_sandbox import graph_safe_page_path

ReadGraphTarget = Literal["page", "memory", "block_ast", "structural_hops", "dashboard"]
SearchGraphMethod = Literal["bm25", "regex", "unlinked_mentions", "journal_tasks"]
MutateGraphAction = Literal["write_outline", "edit_property", "append_journal", "inject_query"]
RefactorBlocksAction = Literal["split_large", "reparent", "generate_flashcards"]
RunLinterName = Literal["unify_tags", "block_refs", "full_wiki_scan"]


def graph_path_from_env() -> str:
    return os.environ.get("LOGSEQ_GRAPH_PATH", "").strip()


def graph_missing_text() -> str:
    return (
        "LOGSEQ_GRAPH_PATH is not set; cannot access the graph on disk. "
        "Set it to your Logseq graph root (the folder that contains `pages/`), then retry."
    )


def graph_missing_dict() -> dict[str, Any]:
    return {"ok": False, "code": "graph_missing", "hint": graph_missing_text()}


def parse_json_object(payload: str, *, field_name: str = "payload") -> dict[str, Any]:
    raw = payload.strip()
    if not raw:
        msg = f"`{field_name}` must be a non-empty JSON object"
        raise ValueError(msg)
    data = json.loads(raw)
    if not isinstance(data, dict):
        msg = f"`{field_name}` must decode to a JSON object"
        raise TypeError(msg)
    return cast(dict[str, Any], data)


def parse_optional_json_query(query: str) -> dict[str, Any]:
    raw = query.strip()
    if not raw:
        return {}
    if raw.startswith("{"):
        data = json.loads(raw)
        if not isinstance(data, dict):
            msg = "`query` JSON must be an object when it starts with `{`"
            raise TypeError(msg)
        return cast(dict[str, Any], data)
    return {}


def read_block_ast_markdown(graph_path: str, query: str) -> str:
    """Return the on-disk Markdown subtree for one block (page title + ``id::`` UUID)."""
    parts = [p.strip() for p in query.split("|", 1)]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        msg = (
            "For `target_type=block_ast`, set `query` to `Page Title|block-uuid` "
            "(Logseq page name, pipe, 36-char block UUID from `id::`)."
        )
        raise ValueError(msg)
    page_ref, block_uuid = parts[0], parts[1]
    path = graph_safe_page_path(graph_path, page_ref)
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines(keepends=True)
    stripped = [ln.rstrip("\n") for ln in lines]
    loc = locate_block_by_uuid(stripped, block_uuid)
    if loc is None:
        return (
            f"Block `{block_uuid}` not found on page `{page_ref}`. "
            "Confirm the UUID matches an `id::` line on that page."
        )
    b_idx, _id_idx, end = loc
    excerpt = "".join(lines[b_idx:end])
    return (
        f"# Block AST excerpt\n\n"
        f"- **Page:** [[{page_ref}]]\n"
        f"- **Block UUID:** `{block_uuid}`\n\n"
        f"```markdown\n{excerpt.rstrip()}\n```\n"
    )


def format_regex_search_markdown(graph_path: str, pattern: str, *, limit: int = 50) -> str:
    """Vault-wide ``pages/**/*.md`` line scan (orchestration; not the spatial parser)."""
    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        msg = f"Invalid regex in `query`: {exc}"
        raise ValueError(msg) from exc

    root = Path(graph_path).expanduser().resolve(strict=False)
    pages = root / "pages"
    if not pages.is_dir():
        return f"{graph_missing_text()}\n\n`pages/` directory is missing."

    hits: list[tuple[str, int, str]] = []
    for path in sorted(pages.rglob("*.md")):
        if not path.is_file():
            continue
        try:
            body = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = path.relative_to(root).as_posix()
        for line_no, line in enumerate(body.splitlines(), start=1):
            if compiled.search(line):
                hits.append((rel, line_no, line.strip()[:240]))
                if len(hits) >= limit:
                    break
        if len(hits) >= limit:
            break

    lines = [
        "# Regex search (pages/)",
        "",
        f"- **Graph:** `{root}`",
        f"- **Pattern:** `{pattern}`",
        f"- **Hits (cap {limit}):** {len(hits)}",
        "",
    ]
    if not hits:
        lines.append("_No matches in `pages/**/*.md`._")
        return "\n".join(lines) + "\n"
    for rel, line_no, preview in hits:
        lines.append(f"- `{rel}`:{line_no} — {preview}")
    lines.append("")
    return "\n".join(lines) + "\n"


__all__ = [
    "MutateGraphAction",
    "ReadGraphTarget",
    "RefactorBlocksAction",
    "RunLinterName",
    "SearchGraphMethod",
    "format_regex_search_markdown",
    "graph_missing_dict",
    "graph_missing_text",
    "graph_path_from_env",
    "parse_json_object",
    "parse_optional_json_query",
    "read_block_ast_markdown",
]
