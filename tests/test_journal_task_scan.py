"""Tests for journal task scanning."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from src.graph.journal_task_scan import (
    append_journal_markdown_section,
    format_journal_task_review_markdown,
    journal_file_path,
    scan_journal_tasks,
    upsert_matryca_activity_block,
)


def test_journal_file_path_naming(tmp_path: Path) -> None:
    p = journal_file_path(tmp_path, date(2026, 5, 18))
    assert p.name == "2026_05_18.md"
    assert p.parent.name == "journals"


def test_scan_journal_tasks_collects_markers(tmp_path: Path) -> None:
    jdir = tmp_path / "journals"
    jdir.mkdir()
    day = date(2026, 5, 18)
    f = journal_file_path(tmp_path, day)
    f.write_text(
        "\n".join(
            [
                "- [[Journal]]",
                "- TODO first task",
                "  SCHEDULED: <2026-05-20 Mon>",
                "- LATER second",
                "  DEADLINE: <2026-05-21 Tue>",
                "- DONE done item",
                "- WAITING blocked",
                "",
            ],
        ),
        encoding="utf-8",
    )
    report = scan_journal_tasks(tmp_path, days=1, as_of=day)
    assert report.files_scanned == 1
    markers = {it.marker for it in report.items}
    assert markers == {"TODO", "LATER", "WAITING"}
    todo = next(i for i in report.items if i.marker == "TODO")
    assert "SCHEDULED:" in (todo.scheduled or "")


def test_nested_task_block(tmp_path: Path) -> None:
    jdir = tmp_path / "journals"
    jdir.mkdir()
    day = date(2026, 5, 10)
    p = journal_file_path(tmp_path, day)
    p.write_text(
        "- TODO parent\n  - nested note\n- WAITING after\n",
        encoding="utf-8",
    )
    report = scan_journal_tasks(tmp_path, days=30, as_of=day)
    parent = next(i for i in report.items if i.headline == "parent")
    assert "nested note" in parent.block_text


def test_format_review_markdown(tmp_path: Path) -> None:
    jdir = tmp_path / "journals"
    jdir.mkdir()
    day = date(2026, 5, 1)
    journal_file_path(tmp_path, day).write_text("- TODO x\n", encoding="utf-8")
    report = scan_journal_tasks(tmp_path, days=5, as_of=day)
    md = format_journal_task_review_markdown(report)
    assert "Task review" in md
    assert "`TODO`" in md


def test_append_journal_section_dry_run(tmp_path: Path) -> None:
    out = append_journal_markdown_section(
        tmp_path,
        "## Hello",
        as_of=date(2026, 5, 18),
        dry_run=True,
    )
    assert out["ok"] is True
    assert out["dry_run"] is True


def test_upsert_matryca_activity_creates_single_bullet(tmp_path: Path) -> None:
    day = date(2026, 6, 5)
    line = "- 🤖 Matryca Activity — indexed 1 page(s); 1 duty cycle(s)"
    out = upsert_matryca_activity_block(tmp_path, line, as_of=day, dry_run=False)
    assert out["ok"] is True
    text = journal_file_path(tmp_path, day).read_text(encoding="utf-8")
    assert text.strip() == line
    assert text.count("🤖 Matryca Activity") == 1


def test_upsert_matryca_activity_replaces_existing_bullet(tmp_path: Path) -> None:
    day = date(2026, 6, 5)
    path = journal_file_path(tmp_path, day)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("- daily note\n- 🤖 Matryca Activity — indexed 1 page(s)\n", encoding="utf-8")
    updated = "- 🤖 Matryca Activity — indexed 3 page(s); 2 duty cycle(s)"
    upsert_matryca_activity_block(tmp_path, updated, as_of=day, dry_run=False)
    text = path.read_text(encoding="utf-8")
    assert "- daily note" in text
    assert "indexed 3 page(s)" in text
    assert "indexed 1 page(s)" not in text
    assert text.count("🤖 Matryca Activity") == 1


def test_upsert_matryca_activity_strips_legacy_sections(tmp_path: Path) -> None:
    day = date(2026, 6, 5)
    path = journal_file_path(tmp_path, day)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "- morning note",
                "",
                "## 🤖 Matryca Activity",
                "- indexed 1 page(s); checked 4 link(s).",
                "## 🤖 Matryca Activity",
                "- indexed 1 page(s); checked 4 link(s).",
                "",
            ],
        ),
        encoding="utf-8",
    )
    line = "- 🤖 Matryca Activity — indexed 2 page(s); checked 8 link(s); 2 duty cycle(s)"
    upsert_matryca_activity_block(tmp_path, line, as_of=day, dry_run=False)
    text = path.read_text(encoding="utf-8")
    assert "## 🤖 Matryca Activity" not in text
    assert "- morning note" in text
    assert "indexed 2 page(s)" in text
    assert text.count("🤖 Matryca Activity") == 1
