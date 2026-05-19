"""Tests for agent-native CLI argparse routing and dispatch."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pytest
from src.cli import build_parser, main, run_cli


def test_parser_exposes_five_subcommands() -> None:
    parser = build_parser()
    sub_action = next(
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)  # noqa: SLF001
    )
    assert sorted(sub_action.choices) == ["lint", "mutate", "read", "refactor", "search"]


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (
            ["read", "page", "My Project"],
            {"command": "read", "target_type": "page", "query": "My Project"},
        ),
        (["read", "memory"], {"command": "read", "target_type": "memory", "query": ""}),
        (
            ["search", "bm25", "redis cache"],
            {"command": "search", "method": "bm25", "query": "redis cache"},
        ),
        (["search", "regex", r"TODO"], {"command": "search", "method": "regex", "query": "TODO"}),
        (
            [
                "mutate",
                "edit_property",
                "--target",
                "Demo|uuid",
                "--payload",
                '{"search":"x","replacement":"y"}',
            ],
            {
                "command": "mutate",
                "action": "edit_property",
                "target": "Demo|uuid",
                "payload": '{"search":"x","replacement":"y"}',
            },
        ),
        (
            ["refactor", "split_large", "Demo Page", "--payload", '{"dry_run": true}'],
            {
                "command": "refactor",
                "action": "split_large",
                "target_uuid": "Demo Page",
                "payload": '{"dry_run": true}',
            },
        ),
        (["lint", "block_refs"], {"command": "lint", "linter_name": "block_refs"}),
    ],
)
def test_parser_routes_subcommands(argv: list[str], expected: dict[str, str]) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    for key, value in expected.items():
        assert getattr(args, key) == value


@pytest.mark.asyncio
async def test_run_cli_read_memory_without_l1(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("MATRYCA_L1_PATH", raising=False)
    monkeypatch.delenv("LOGSEQ_GRAPH_PATH", raising=False)
    args = Namespace(command="read", target_type="memory", query="")
    code = await run_cli(args)
    out = capsys.readouterr().out
    assert code == 0
    assert "No L1 memory loaded" in out


@pytest.mark.asyncio
async def test_run_cli_search_regex(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pages = tmp_path / "pages"
    pages.mkdir()
    (pages / "Hit.md").write_text("- TODO fix item\n", encoding="utf-8")
    monkeypatch.setenv("LOGSEQ_GRAPH_PATH", str(tmp_path))

    args = Namespace(command="search", method="regex", query="TODO")
    code = await run_cli(args)
    out = capsys.readouterr().out
    assert code == 0
    assert "Hit.md" in out


@pytest.mark.asyncio
async def test_run_cli_refactor_split_large_dry_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pages = tmp_path / "pages"
    pages.mkdir()
    (pages / "Demo.md").write_text("- Short note\n", encoding="utf-8")
    monkeypatch.setenv("LOGSEQ_GRAPH_PATH", str(tmp_path))

    args = Namespace(
        command="refactor",
        action="split_large",
        target_uuid="Demo",
        payload='{"dry_run": true}',
    )
    code = await run_cli(args)
    captured = capsys.readouterr()
    assert code == 0
    payload = json.loads(captured.out)
    assert payload.get("dry_run") is True


@pytest.mark.asyncio
async def test_run_cli_lint_block_refs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pages = tmp_path / "pages"
    pages.mkdir()
    (pages / "Demo.md").write_text("- [[Link]]\n", encoding="utf-8")
    monkeypatch.setenv("LOGSEQ_GRAPH_PATH", str(tmp_path))

    args = Namespace(command="lint", linter_name="block_refs")
    code = await run_cli(args)
    out = capsys.readouterr().out
    assert code == 0
    assert "block" in out.lower() or "ref" in out.lower()


def test_main_invalid_json_payload_exits_one(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("LOGSEQ_GRAPH_PATH", "/tmp/unused")
    monkeypatch.setenv("LOGSEQ_API_TOKEN", "test-token")
    with patch("src.cli.build_logseq_bridge") as mock_bridge:
        mock_bridge.return_value.aclose = lambda: None
        with pytest.raises(SystemExit) as exc:
            main(
                [
                    "mutate",
                    "write_outline",
                    "--target",
                    "parent-uuid",
                    "--payload",
                    "not-json",
                ],
            )
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert err


def test_subprocess_read_memory_routes() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "src.cli", "read", "memory"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert proc.stdout


def test_subprocess_missing_subcommand_exits_nonzero() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "src.cli"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0
    assert "required" in proc.stderr.lower() or "usage" in proc.stderr.lower()
