"""Tests for surgical property-line edits."""

from __future__ import annotations

from pathlib import Path

from src.graph.property_line_edit import edit_block_property_lines


def _sample_page(uuid_line: str = "11111111-1111-4111-8111-111111111111") -> str:
    return "\n".join(
        [
            "- Root block",
            f"  id:: {uuid_line}",
            "  type:: alpha",
            "  domain:: tech",
            "- Sibling",
            "",
        ]
    )


def test_property_line_dry_run(tmp_path: Path) -> None:
    pages = tmp_path / "pages"
    pages.mkdir(parents=True)
    (pages / "Demo.md").write_text(_sample_page(), encoding="utf-8")

    out = edit_block_property_lines(
        tmp_path,
        "Demo",
        "11111111-1111-4111-8111-111111111111",
        "alpha",
        "beta",
        dry_run=True,
        use_regex=False,
        replace_all=False,
    )
    assert out.ok and out.code == "dry_run_ok"
    assert out.match_count == 1
    assert pages.joinpath("Demo.md").read_text().find("type:: alpha") >= 0


def test_property_line_apply_and_backup(tmp_path: Path) -> None:
    pages = tmp_path / "pages"
    pages.mkdir(parents=True)
    (pages / "Demo.md").write_text(_sample_page(), encoding="utf-8")

    out = edit_block_property_lines(
        tmp_path,
        "Demo",
        "11111111-1111-4111-8111-111111111111",
        "alpha",
        "beta",
        dry_run=False,
        use_regex=False,
        replace_all=False,
    )
    assert out.ok and out.code == "applied"
    text = (pages / "Demo.md").read_text(encoding="utf-8")
    assert "type:: beta" in text
    assert (pages / "Demo.md.bak").is_file()


def test_regex_capture_replacement(tmp_path: Path) -> None:
    pages = tmp_path / "pages"
    pages.mkdir(parents=True)
    (pages / "Demo.md").write_text(_sample_page(), encoding="utf-8")

    out = edit_block_property_lines(
        tmp_path,
        "Demo",
        "11111111-1111-4111-8111-111111111111",
        r"type:: (\w+)",
        r"type:: \g<1>-x",
        dry_run=True,
        use_regex=True,
        replace_all=False,
    )
    assert out.ok
    assert "alpha-x" in "".join(out.previews)


def test_append_page_alias_to_existing_line(tmp_path: Path) -> None:
    from src.graph.property_line_edit import append_page_alias_line

    pages = tmp_path / "pages"
    pages.mkdir(parents=True)
    (pages / "Topic.md").write_text(
        "alias:: [[One]], Two\n",
        encoding="utf-8",
    )
    out = append_page_alias_line(tmp_path, "Topic", "Three", dry_run=False)
    assert out.ok and out.added
    text = (pages / "Topic.md").read_text(encoding="utf-8")
    assert "Three" in text
    dup = append_page_alias_line(tmp_path, "Topic", "three", dry_run=True)
    assert dup.code == "noop_duplicate"


def test_append_page_alias_creates_line(tmp_path: Path) -> None:
    from src.graph.property_line_edit import append_page_alias_line

    pages = tmp_path / "pages"
    pages.mkdir(parents=True)
    (pages / "Empty.md").write_text("- root\n", encoding="utf-8")
    out = append_page_alias_line(tmp_path, "Empty", "NewAlias", dry_run=False)
    assert out.ok and out.added
    assert "alias::" in (pages / "Empty.md").read_text(encoding="utf-8")
