"""Route ``matryca-plumber`` to the CLI or MCP stdio server by invocation shape."""

from __future__ import annotations

import sys

from .cli import main as cli_main

_PLUMBER_SHORTHAND: frozenset[str] = frozenset(
    {"start", "status", "stop", "ui", "audit", "cluster"},
)
_CLI_COMMANDS: frozenset[str] = frozenset(
    {
        "read",
        "search",
        "mutate",
        "refactor",
        "lint",
        "service",
        "plumber",
        *_PLUMBER_SHORTHAND,
    },
)


def _normalize_cli_argv(argv: list[str]) -> list[str] | None:
    """Return CLI argv when ``argv`` selects the agent CLI; otherwise ``None``."""
    if not argv:
        return None
    if argv[0] in ("-h", "--help"):
        return argv
    if argv[0] not in _CLI_COMMANDS:
        return None
    if argv[0] in _PLUMBER_SHORTHAND:
        return ["plumber", *argv]
    return argv


def main() -> None:
    """CLI entrypoint for the ``matryca-plumber`` console script."""
    cli_argv = _normalize_cli_argv(sys.argv[1:])
    if cli_argv is not None:
        cli_main(cli_argv)
        return
    from .main import main as mcp_main

    mcp_main()


if __name__ == "__main__":
    main()
