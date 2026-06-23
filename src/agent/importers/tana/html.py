"""Strip Tana ``props.name`` HTML to plain text for Logseq property keys and values."""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser

_TAG_RE = re.compile(r"<[^>]+>")


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data:
            self._parts.append(data)

    def handle_entityref(self, name: str) -> None:
        self._parts.append(html.unescape(f"&{name};"))

    def handle_charref(self, name: str) -> None:
        self._parts.append(html.unescape(f"&#{name};"))


def plain_text_from_tana_html(raw: str) -> str:
    """Convert Tana HTML ``props.name`` (inline refs, spans) to plain text."""
    if not raw:
        return ""
    if "<" not in raw and "&" not in raw:
        return raw.strip()
    parser = _HTMLTextExtractor()
    try:
        parser.feed(raw)
        parser.close()
        text = "".join(parser._parts)
    except Exception:
        text = _TAG_RE.sub("", raw)
    return html.unescape(text).strip()


__all__ = ["plain_text_from_tana_html"]
