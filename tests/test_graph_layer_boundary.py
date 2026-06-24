"""Graph layer must not import agent orchestration modules."""

from __future__ import annotations

from pathlib import Path


def test_graph_modules_do_not_import_agent() -> None:
    graph_dir = Path(__file__).resolve().parents[1] / "src" / "graph"
    offenders: list[str] = []
    for path in sorted(graph_dir.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "from ..agent" in text or "from src.agent" in text:
            offenders.append(str(path.relative_to(graph_dir.parents[1])))
    assert offenders == []


def test_graph_modules_do_not_import_daemon() -> None:
    graph_dir = Path(__file__).resolve().parents[1] / "src" / "graph"
    offenders: list[str] = []
    for path in sorted(graph_dir.rglob("*.py")):
        if path.name == "daemon_checkpoint.py":
            continue
        text = path.read_text(encoding="utf-8")
        if "from ..daemon" in text or "from src.daemon" in text:
            offenders.append(str(path.relative_to(graph_dir.parents[1])))
    assert offenders == []
