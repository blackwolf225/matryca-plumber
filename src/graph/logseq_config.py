"""Read operator settings from ``logseq/config.edn`` inside a Logseq OG vault."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import edn_format
from edn_format import Keyword
from loguru import logger

from .path_sandbox import read_graph_file_text

DEFAULT_JOURNAL_PAGE_TITLE_FORMAT = "yyyy-MM-dd"
_JOURNAL_FORMAT_KEY = Keyword("journal/page-title-format")
_CONFIG_REL = Path("logseq") / "config.edn"
_PEEK_BYTES = 8192


@dataclass(frozen=True, slots=True)
class JournalFormatResult:
    """Outcome of resolving ``:journal/page-title-format`` from ``config.edn``."""

    format_string: str
    warning: str | None = None
    source: str = "default"


def _normalize_journal_format(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value).strip() or None


def _extract_journal_format_from_edn(text: str) -> str | None:
    parsed = edn_format.loads(text)
    if not isinstance(parsed, Mapping):
        return None
    for key, val in parsed.items():
        if key == _JOURNAL_FORMAT_KEY or str(key).lstrip(":") == "journal/page-title-format":
            return _normalize_journal_format(val)
    return None


def read_logseq_config_map(vault_path: str | Path) -> Mapping[str, Any] | None:
    """Parse ``logseq/config.edn`` into a string-keyed map, or ``None`` on failure."""
    root = Path(vault_path).expanduser()
    config_path = root / _CONFIG_REL
    if not config_path.is_file():
        return None
    try:
        text = read_graph_file_text(config_path, root)
        parsed = edn_format.loads(text)
    except (OSError, edn_format.EDNDecodeError, ValueError, TypeError):
        return None
    if not isinstance(parsed, Mapping):
        return None
    out: dict[str, Any] = {}
    for key, val in parsed.items():
        out[str(key).lstrip(":")] = val
    return out


def _config_string_value(config: Mapping[str, Any], key: str) -> str | None:
    val = config.get(key)
    return _normalize_journal_format(val)


def get_logseq_journal_file_name_format(vault_path: str | Path) -> str | None:
    """Optional ``:journal/file-name-format`` from ``config.edn`` (``None`` when unset)."""
    config = read_logseq_config_map(vault_path)
    if config is None:
        return None
    return _config_string_value(config, "journal/file-name-format")


def get_logseq_journal_format(vault_path: str | Path) -> JournalFormatResult:
    """Read ``:journal/page-title-format`` from ``logseq/config.edn``.

    Falls back to Logseq's default ``yyyy-MM-dd`` when the file is missing,
    unreadable, or does not define the key. Never raises — callers get a
    ``JournalFormatResult`` with an optional ``warning`` string.
    """
    root = Path(vault_path).expanduser()
    config_path = root / _CONFIG_REL
    if not config_path.is_file():
        return JournalFormatResult(
            format_string=DEFAULT_JOURNAL_PAGE_TITLE_FORMAT,
            warning="logseq/config.edn not found; using default journal format",
            source="default",
        )
    try:
        text = read_graph_file_text(config_path, root)
    except OSError as exc:
        logger.warning("Failed to read {}: {}", config_path, exc)
        return JournalFormatResult(
            format_string=DEFAULT_JOURNAL_PAGE_TITLE_FORMAT,
            warning=f"could not read config.edn: {exc}",
            source="default",
        )
    try:
        fmt = _extract_journal_format_from_edn(text)
    except (edn_format.EDNDecodeError, ValueError, TypeError) as exc:
        logger.warning("Failed to parse {}: {}", config_path, exc)
        return JournalFormatResult(
            format_string=DEFAULT_JOURNAL_PAGE_TITLE_FORMAT,
            warning=f"malformed config.edn: {exc}",
            source="default",
        )
    if not fmt:
        return JournalFormatResult(
            format_string=DEFAULT_JOURNAL_PAGE_TITLE_FORMAT,
            warning="journal/page-title-format missing in config.edn",
            source="default",
        )
    return JournalFormatResult(format_string=fmt, source="config.edn")


__all__ = [
    "DEFAULT_JOURNAL_PAGE_TITLE_FORMAT",
    "JournalFormatResult",
    "get_logseq_journal_file_name_format",
    "get_logseq_journal_format",
    "read_logseq_config_map",
]
