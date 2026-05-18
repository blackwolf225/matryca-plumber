"""Index ``alias::`` lines across the graph for entity resolution (line/regex scan only).

Normalization is **intentionally shallow** (casefold, trim, collapse whitespace, strip
wikilink brackets): there is no fuzzy edit-distance matching and no extra dependencies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

_ALIAS_LINE = re.compile(r"(?im)^\s*alias::\s*(.+?)\s*$")


def normalize_concept_key(value: str) -> str:
    """Normalize a page title or alias fragment for dictionary lookup."""
    t = value.strip()
    t = t.strip("[]").strip()
    t = re.sub(r"\s+", " ", t)
    return t.casefold()


def _split_alias_segments(raw: str) -> list[str]:
    """Split ``alias::`` payload on commas (Logseq's common multi-alias form)."""
    out: list[str] = []
    for chunk in raw.split(","):
        c = chunk.strip()
        if c:
            out.append(c)
    return out


def _iter_markdown_files(graph_root: Path) -> list[Path]:
    pages = graph_root / "pages"
    journals = graph_root / "journals"
    files: list[Path] = []
    if pages.is_dir():
        files.extend(sorted(pages.rglob("*.md")))
    if journals.is_dir():
        files.extend(sorted(journals.rglob("*.md")))
    return files


def page_title_from_path(graph_root: Path, path: Path) -> str:
    """Derive Logseq-style page title from a path under ``pages/`` or ``journals/``."""
    rel = path.relative_to(graph_root)
    return rel.with_suffix("").as_posix().replace("pages/", "").replace("journals/", "")


@dataclass
class AliasIndex:
    """In-memory alias map built from a single graph scan."""

    graph_root: str
    alias_to_page: dict[str, str] = field(default_factory=dict)
    page_to_aliases: dict[str, list[str]] = field(default_factory=dict)
    page_to_relpath: dict[str, str] = field(default_factory=dict)
    collision_notes: list[str] = field(default_factory=list)

    def resolve(self, candidate: str) -> ResolvedEntity:
        """Resolve one candidate against titles and aliases."""
        norm = normalize_concept_key(candidate)
        collisions: list[str] = []
        if not norm:
            return ResolvedEntity(
                candidate=candidate,
                normalized=norm,
                matched=False,
                canonical_page_title=None,
                page_relative_path=None,
                matched_via="none",
                existing_aliases=[],
                collisions=[],
                safe_to_create_new_page=False,
            )

        # Title match (page stem / journal stem as indexed)
        for title, rel in self.page_to_relpath.items():
            if normalize_concept_key(title) == norm:
                aliases = list(self.page_to_aliases.get(title, []))
                return ResolvedEntity(
                    candidate=candidate,
                    normalized=norm,
                    matched=True,
                    canonical_page_title=title,
                    page_relative_path=rel,
                    matched_via="title",
                    existing_aliases=aliases,
                    collisions=collisions,
                    safe_to_create_new_page=False,
                )

        page = self.alias_to_page.get(norm)
        if page:
            aliases = list(self.page_to_aliases.get(page, []))
            return ResolvedEntity(
                candidate=candidate,
                normalized=norm,
                matched=True,
                canonical_page_title=page,
                page_relative_path=self.page_to_relpath.get(page),
                matched_via="alias",
                existing_aliases=aliases,
                collisions=collisions,
                safe_to_create_new_page=False,
            )

        return ResolvedEntity(
            candidate=candidate,
            normalized=norm,
            matched=False,
            canonical_page_title=None,
            page_relative_path=None,
            matched_via="none",
            existing_aliases=[],
            collisions=collisions,
            safe_to_create_new_page=True,
        )


@dataclass(frozen=True, slots=True)
class ResolvedEntity:
    candidate: str
    normalized: str
    matched: bool
    canonical_page_title: str | None
    page_relative_path: str | None
    matched_via: Literal["none", "title", "alias"]
    existing_aliases: list[str]
    collisions: list[str]
    safe_to_create_new_page: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "candidate": self.candidate,
            "normalized": self.normalized,
            "matched": self.matched,
            "canonical_page_title": self.canonical_page_title,
            "page_relative_path": self.page_relative_path,
            "matched_via": self.matched_via,
            "existing_aliases": list(self.existing_aliases),
            "collisions": list(self.collisions),
            "safe_to_create_new_page": self.safe_to_create_new_page,
        }


def iter_alias_source_paths(graph_root: str | Path) -> list[Path]:
    """Markdown paths scanned by :func:`build_alias_index` (stable sort)."""
    return _iter_markdown_files(Path(graph_root).expanduser().resolve(strict=False))


def build_alias_index(graph_root: str | Path) -> AliasIndex:
    """Walk ``pages/**/*.md`` and ``journals/**/*.md`` collecting ``alias::`` lines."""
    root = Path(graph_root).expanduser().resolve(strict=False)
    idx = AliasIndex(graph_root=str(root))
    for path in _iter_markdown_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            idx.collision_notes.append(f"unreadable {path}: {exc}")
            continue
        rel = path.relative_to(root).as_posix()
        title = page_title_from_path(root, path)
        idx.page_to_relpath.setdefault(title, rel)

        aliases_found: list[str] = []
        for match in _ALIAS_LINE.finditer(text):
            segments = _split_alias_segments(match.group(1))
            for seg in segments:
                aliases_found.append(seg)
                nk = normalize_concept_key(seg)
                if not nk:
                    continue
                existing = idx.alias_to_page.get(nk)
                if existing and existing != title:
                    idx.collision_notes.append(
                        f"alias `{seg}` ({nk!r}) maps to both `{existing}` and `{title}`; "
                        f"keeping `{existing}`",
                    )
                    continue
                if nk not in idx.alias_to_page:
                    idx.alias_to_page[nk] = title
        if aliases_found:
            idx.page_to_aliases[title] = aliases_found
    return idx


__all__ = [
    "AliasIndex",
    "ResolvedEntity",
    "build_alias_index",
    "iter_alias_source_paths",
    "normalize_concept_key",
    "page_title_from_path",
]
