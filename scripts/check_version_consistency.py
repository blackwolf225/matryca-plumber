#!/usr/bin/env python3
"""Fail CI when llms.txt version headers drift from pyproject.toml."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def pyproject_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if match is None:
        msg = "Could not parse version from pyproject.toml"
        raise SystemExit(msg)
    return match.group(1)


def check_llms_header(path: Path, version: str) -> None:
    first_line = path.read_text(encoding="utf-8").splitlines()[0]
    expected = f"v{version}"
    if expected not in first_line:
        rel = path.relative_to(ROOT)
        msg = f"{rel}: first line must reference {expected!r}, got: {first_line!r}"
        raise SystemExit(msg)


def main() -> None:
    version = pyproject_version()
    for rel in ("llms.txt", ".well-known/llms.txt"):
        check_llms_header(ROOT / rel, version)
    print(f"version consistency OK (pyproject.toml = {version})")


if __name__ == "__main__":
    main()
