"""RAG-facing adapter for Logseq spatial context.

Indentation-aware structure, spatial nesting, ``id::`` UUID extraction, block
reference handling, and related graph semantics are implemented exclusively in
the external **logseq-matryca-parser** package (single source of truth). This
module stays a thin orchestration boundary so **matryca-logseq-llm-wiki** can
consume parsed pages without duplicating parser logic—aligned with publishing
that library on PyPI later.
"""

from __future__ import annotations

from typing import Any


def get_spatial_context(file_path: str) -> Any:
    """Load ``file_path`` and return the parser-owned page graph.

    All heavy lifting is delegated to ``logseq_matryca_parser``. The import is
    performed inside this function so a future public API rename or submodule
    split in the upstream package only requires updating this adapter, not every
    consumer of ``matryca_hooks``.

    Args:
        file_path: Path to a Logseq ``.md`` page on disk (absolute or relative).

    Returns:
        The parsed graph model from the external package (currently
        ``LogosParser().parse_page_file(...)`` → ``LogseqPage``).

    Raises:
        ImportError: If ``logseq-matryca-parser`` is not installed.
        OSError: If the file cannot be read (propagated from the parser).
    """
    from logseq_matryca_parser import LogosParser

    return LogosParser().parse_page_file(file_path)
