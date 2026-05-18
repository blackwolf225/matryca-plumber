"""Global fence / dead-zone scan for whole-page Markdown (Logseq OG).

Line indices that must not be edited as Logseq surface: fenced code (```),
HTML ``<!-- ... -->`` comments, and ``#+BEGIN_QUERY`` … ``#+END_QUERY`` blocks.

HTML and query detection is **masked** while inside Markdown code fences so
``<!--`` / ``#+BEGIN`` inside fenced code do not corrupt global state.
"""

from __future__ import annotations

import re
from typing import Final

_BEGIN_QUERY: Final = "#+BEGIN_QUERY"
_END_QUERY: Final = "#+END_QUERY"

_MD_FENCE_OPEN: Final = re.compile(r"^( {0,3})(`{3,})([^`]*)$")
_MD_FENCE_CLOSE: Final = re.compile(r"^( {0,3})(`{3,})\s*$")


def _strip_eol(s: str) -> str:
    return s.rstrip("\r\n")


def _is_begin_query(line: str) -> bool:
    t = line.lstrip()
    return t.startswith(_BEGIN_QUERY) and (
        len(t) == len(_BEGIN_QUERY) or t[len(_BEGIN_QUERY)] in " \t"
    )


def _is_end_query(line: str) -> bool:
    t = line.lstrip()
    return t.startswith(_END_QUERY) and (len(t) == len(_END_QUERY) or t[len(_END_QUERY)] in " \t")


def _scan_html_line(line: str, *, in_comment: bool) -> tuple[bool, bool]:
    """(line_overlaps_comment, in_comment_after_line)."""
    pos = 0
    overlaps = in_comment
    in_c = in_comment
    while pos <= len(line):
        if in_c:
            overlaps = True
            close_at = line.find("-->", pos)
            if close_at < 0:
                return True, True
            in_c = False
            pos = close_at + 3
            continue
        open_at = line.find("<!--", pos)
        if open_at < 0:
            return overlaps, False
        overlaps = True
        in_c = True
        pos = open_at + 4
    return overlaps, in_c


def _update_md_fence(line: str, *, in_ticks: int) -> int:
    """Return new fence tick count (0 = not inside fence)."""
    if in_ticks:
        cm = _MD_FENCE_CLOSE.match(line)
        if cm is not None and len(cm.group(2)) >= in_ticks:
            return 0
        return in_ticks
    op = _MD_FENCE_OPEN.match(line)
    if op is None:
        return 0
    return len(op.group(2))


def _protected_md_lines(lines: list[str]) -> set[int]:
    protected: set[int] = set()
    ticks = 0
    for i, raw in enumerate(lines):
        line = _strip_eol(raw)
        if ticks:
            protected.add(i)
        new_ticks = _update_md_fence(line, in_ticks=ticks)
        if new_ticks and not ticks:
            protected.add(i)
        ticks = new_ticks
    return protected


def _protected_query_lines(lines: list[str]) -> set[int]:
    protected: set[int] = set()
    md_ticks = 0
    in_q = False
    for i, raw in enumerate(lines):
        line = _strip_eol(raw)
        md_ticks = _update_md_fence(line, in_ticks=md_ticks)
        if md_ticks:
            continue
        if in_q:
            protected.add(i)
            if _is_end_query(line):
                in_q = False
            continue
        if _is_begin_query(line):
            protected.add(i)
            in_q = True
    return protected


def _protected_html_lines(lines: list[str]) -> set[int]:
    protected: set[int] = set()
    md_ticks = 0
    in_html = False
    for i, raw in enumerate(lines):
        line = _strip_eol(raw)
        md_ticks = _update_md_fence(line, in_ticks=md_ticks)
        if md_ticks:
            continue
        overlap, in_html = _scan_html_line(line, in_comment=in_html)
        if overlap:
            protected.add(i)
    return protected


def compute_page_protected_line_indices(file_content: str) -> set[int]:
    """Return 0-based line indices inside fenced code, HTML comments, or advanced queries."""
    lines = file_content.splitlines()
    return _protected_md_lines(lines) | _protected_query_lines(lines) | _protected_html_lines(lines)


__all__ = ["compute_page_protected_line_indices"]
