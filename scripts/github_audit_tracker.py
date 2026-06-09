#!/usr/bin/env python3
"""Populate GitHub milestones and issues from the v1.9.x perfection audit.

Uses the GitHub CLI (`gh`) and the REST API for milestones. Designed for
idempotent, rate-limited bulk issue creation with interactive confirmation.

Usage:
    # Interactive (default): prompts before creating anything
    python3 scripts/github_audit_tracker.py

    # Preview without API writes
    python3 scripts/github_audit_tracker.py --dry-run

    # Non-interactive (CI / scripted)
    python3 scripts/github_audit_tracker.py --yes

    # Override repository (default: current `gh` context)
    python3 scripts/github_audit_tracker.py --repo owner/name

Requirements:
    - `gh` authenticated with `repo` scope: `gh auth status`
    - Python 3.12+ (stdlib only)

Data source:
    scripts/data/v1_9_perfection_audit_issues.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_FILE = SCRIPT_DIR / "data" / "v1_9_perfection_audit_issues.json"
ISSUE_CREATE_DELAY_SECONDS = 2.0

# Maps audit category → GitHub label(s). "bug" is a GitHub default label.
CATEGORY_LABELS: dict[str, list[str]] = {
    "Security": ["security"],
    "Bug": ["bug"],
    "Performance": ["performance"],
    "Tech Debt": ["tech-debt"],
}

# Prefix for idempotent title matching (survives re-runs).
AUDIT_TITLE_MARKER = "[v1.9.x Audit"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MilestoneSpec:
    title: str
    description: str


@dataclass(frozen=True, slots=True)
class LabelSpec:
    name: str
    description: str
    color: str


@dataclass(frozen=True, slots=True)
class IssueSpec:
    id: int
    title: str
    category: str
    milestone: str
    impact: str
    problem: str
    solution: str
    files: list[str]


# ---------------------------------------------------------------------------
# GitHub CLI helpers
# ---------------------------------------------------------------------------


class GhError(RuntimeError):
    """Raised when a `gh` subprocess fails."""


def run_gh(
    *args: str,
    input_text: str | None = None,
    check: bool = True,
) -> str:
    """Run `gh` and return stdout. Raises GhError on failure."""
    cmd = ["gh", *args]
    try:
        proc = subprocess.run(
            cmd,
            input=input_text,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise GhError("GitHub CLI (`gh`) not found. Install: https://cli.github.com/") from exc

    if check and proc.returncode != 0:
        stderr = proc.stderr.strip() or proc.stdout.strip()
        raise GhError(f"gh {' '.join(args)} failed ({proc.returncode}): {stderr}")
    return proc.stdout.strip()


def resolve_repo(explicit: str | None) -> str:
    """Return `owner/repo` from --repo or current gh context."""
    if explicit:
        return explicit
    return run_gh("repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner")


def gh_auth_preflight(repo: str) -> None:
    """Verify gh authentication and write access (label probe)."""
    try:
        run_gh("auth", "status")
    except GhError as exc:
        raise GhError(f"{exc}\nRun: gh auth login") from exc

    probe = "_matryca_audit_write_probe"
    try:
        run_gh(
            "label",
            "create",
            probe,
            "--repo",
            repo,
            "--description",
            "write probe",
            "--color",
            "000000",
        )
        run_gh("label", "delete", probe, "--repo", repo, "--yes")
    except GhError as exc:
        raise GhError(
            f"{exc}\nToken may lack write access. Run:\n  gh auth refresh -h github.com -s repo"
        ) from exc


# ---------------------------------------------------------------------------
# Label management
# ---------------------------------------------------------------------------


def ensure_labels(repo: str, labels: list[LabelSpec], *, dry_run: bool) -> None:
    """Create labels if missing (idempotent)."""
    for spec in labels:
        if dry_run:
            print(f"  [dry-run] would ensure label: {spec.name}")
            continue
        try:
            run_gh(
                "label",
                "create",
                spec.name,
                "--repo",
                repo,
                "--description",
                spec.description,
                "--color",
                spec.color,
            )
            print(f"  created label: {spec.name}")
        except GhError:
            # Label already exists — expected on re-run.
            print(f"  label exists: {spec.name}")


# ---------------------------------------------------------------------------
# Milestone management (GitHub REST API via `gh api`)
# ---------------------------------------------------------------------------


def list_milestones(repo: str) -> dict[str, int]:
    """Return mapping milestone_title → milestone_number (open + closed)."""
    raw = run_gh(
        "api",
        f"repos/{repo}/milestones?state=all&per_page=100",
        "--paginate",
    )
    # Paginate may return multiple JSON arrays; gh joins with newlines.
    milestones: list[dict[str, Any]] = []
    for chunk in raw.split("\n"):
        chunk = chunk.strip()
        if not chunk:
            continue
        parsed = json.loads(chunk)
        if isinstance(parsed, list):
            milestones.extend(parsed)
        else:
            milestones.append(parsed)

    return {m["title"]: int(m["number"]) for m in milestones if "title" in m}


def ensure_milestones(
    repo: str,
    specs: list[MilestoneSpec],
    *,
    dry_run: bool,
) -> dict[str, int]:
    """Create missing milestones; return title → number map."""
    existing = {} if dry_run else list_milestones(repo)
    result = dict(existing)

    for spec in specs:
        if spec.title in result:
            print(f"  milestone exists: {spec.title} (#{result[spec.title]})")
            continue

        if dry_run:
            print(f"  [dry-run] would create milestone: {spec.title}")
            result[spec.title] = -1
            continue

        number_raw = run_gh(
            "api",
            f"repos/{repo}/milestones",
            "-f",
            f"title={spec.title}",
            "-f",
            f"description={spec.description}",
            "--jq",
            ".number",
        )
        number = int(number_raw)
        result[spec.title] = number
        print(f"  created milestone: {spec.title} (#{number})")

    return result


# ---------------------------------------------------------------------------
# Issue management
# ---------------------------------------------------------------------------


def format_issue_title(issue: IssueSpec) -> str:
    """Build canonical GitHub issue title with category prefix and audit marker."""
    category_tag = {
        "Security": "Security",
        "Bug": "Bug",
        "Performance": "Performance",
        "Tech Debt": "Tech Debt",
    }.get(issue.category, issue.category)
    return f"[{category_tag}] {issue.title} {AUDIT_TITLE_MARKER} #{issue.id:02d}]"


def format_issue_body(
    issue: IssueSpec,
    *,
    audit_source: str,
    codebase_version: str,
) -> str:
    """Render issue body per GitHub workflow standards."""
    files_md = "\n".join(f"- `{path}`" for path in issue.files)
    return f"""## Problem Description

{issue.problem}

## Proposed Architectural Solution

{issue.solution}

## Estimated Impact

{issue.impact}

## Files Involved

{files_md}

---

**Audit metadata**
- Source: `{audit_source}`
- Codebase version at audit: `{codebase_version}`
- Audit issue ID: #{issue.id}
- Category: {issue.category}
- Milestone: {issue.milestone}

_Closes when merged with tests green (`make check`) and CHANGELOG updated per `06-auto-changelog.mdc`._
"""


def issue_labels(issue: IssueSpec) -> list[str]:
    """Compose label list for an issue."""
    base = list(CATEGORY_LABELS.get(issue.category, []))
    base.extend(["v1.9.x", "audit-2026"])
    # Deduplicate preserving order
    seen: set[str] = set()
    out: list[str] = []
    for label in base:
        if label not in seen:
            seen.add(label)
            out.append(label)
    return out


def find_existing_issue(repo: str, title: str) -> int | None:
    """Return issue number if an issue with exact title exists."""
    try:
        raw = run_gh(
            "issue",
            "list",
            "--repo",
            repo,
            "--state",
            "all",
            "--search",
            f'in:title "{title}"',
            "--json",
            "number,title",
            "--limit",
            "5",
        )
    except GhError:
        return None

    if not raw:
        return None
    items = json.loads(raw)
    for item in items:
        if item.get("title") == title:
            return int(item["number"])
    return None


def create_issue(
    repo: str,
    issue: IssueSpec,
    *,
    audit_source: str,
    codebase_version: str,
    dry_run: bool,
) -> int | None:
    """Create one issue; return issue number or None if skipped."""
    title = format_issue_title(issue)
    existing = None if dry_run else find_existing_issue(repo, title)

    if existing is not None:
        print(f"  skip (exists): #{existing} {title}")
        return existing

    body = format_issue_body(
        issue,
        audit_source=audit_source,
        codebase_version=codebase_version,
    )
    labels = issue_labels(issue)
    label_arg = ",".join(labels)

    if dry_run:
        print(f"  [dry-run] would create: {title}")
        print(f"            milestone={issue.milestone} labels={label_arg}")
        return None

    url = run_gh(
        "issue",
        "create",
        "--repo",
        repo,
        "--title",
        title,
        "--body",
        body,
        "--milestone",
        issue.milestone,
        "--label",
        label_arg,
    )
    # gh prints URL like https://github.com/owner/repo/issues/42
    number = int(url.rstrip("/").split("/")[-1])
    print(f"  created: #{number} {title}")
    return number


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_audit_data(
    path: Path,
) -> tuple[str, str, list[MilestoneSpec], list[LabelSpec], list[IssueSpec]]:
    """Parse JSON audit data file."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    audit_source = str(raw.get("audit_source", path.name))
    codebase_version = str(raw.get("codebase_version", "unknown"))

    milestones = [
        MilestoneSpec(title=m["title"], description=m["description"]) for m in raw["milestones"]
    ]
    labels = [
        LabelSpec(name=l["name"], description=l["description"], color=l["color"])
        for l in raw["labels"]
    ]
    issues = [
        IssueSpec(
            id=int(i["id"]),
            title=i["title"],
            category=i["category"],
            milestone=i["milestone"],
            impact=i["impact"],
            problem=i["problem"],
            solution=i["solution"],
            files=list(i["files"]),
        )
        for i in raw["issues"]
    ]
    return audit_source, codebase_version, milestones, labels, issues


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def confirm(prompt: str) -> bool:
    """Interactive y/N confirmation."""
    try:
        answer = input(f"{prompt} [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        return False
    return answer in {"y", "yes"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create v1.9.x perfection audit milestones and issues on GitHub.",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA_FILE,
        help=f"Audit JSON data file (default: {DEFAULT_DATA_FILE})",
    )
    parser.add_argument(
        "--repo",
        default=None,
        help="Target repository owner/name (default: current gh context)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions without calling GitHub API",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip interactive confirmation prompt",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=ISSUE_CREATE_DELAY_SECONDS,
        help=f"Seconds between issue creations (default: {ISSUE_CREATE_DELAY_SECONDS})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not args.data.is_file():
        print(f"ERROR: data file not found: {args.data}", file=sys.stderr)
        return 1

    audit_source, codebase_version, milestones, labels, issues = load_audit_data(args.data)

    print("== Matryca Plumber — v1.9.x Perfection Audit Tracker ==")
    print(f"Data file:     {args.data}")
    print(f"Audit source:  {audit_source}")
    print(f"Code version:  {codebase_version}")
    print(f"Issues:        {len(issues)}")
    print(f"Milestones:    {len(milestones)}")
    print(f"Mode:          {'DRY-RUN' if args.dry_run else 'LIVE'}")

    repo = args.repo or "(gh context)"
    if not args.dry_run:
        try:
            repo = resolve_repo(args.repo)
            gh_auth_preflight(repo)
        except GhError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    print(f"Repository:    {repo}")
    print()

    if not args.dry_run and not args.yes:
        if not confirm(
            f"This will create up to {len(milestones)} milestones and {len(issues)} "
            f"issues on {repo}. Continue?"
        ):
            print("Cancelled.")
            return 0

    created_issues = 0
    skipped_issues = 0

    print("== Step 1: Labels ==")
    ensure_labels(repo, labels, dry_run=args.dry_run)
    print()

    print("== Step 2: Milestones ==")
    ensure_milestones(repo, milestones, dry_run=args.dry_run)
    print()

    print("== Step 3: Issues ==")
    for index, issue in enumerate(issues, start=1):
        print(f"[{index}/{len(issues)}] audit #{issue.id}")
        try:
            number = create_issue(
                repo,
                issue,
                audit_source=audit_source,
                codebase_version=codebase_version,
                dry_run=args.dry_run,
            )
        except GhError as exc:
            print(f"  ERROR: {exc}", file=sys.stderr)
            print(
                "  Stopping issue loop to avoid partial state confusion.",
                file=sys.stderr,
            )
            return 1

        if number is None and not args.dry_run:
            skipped_issues += 1
        elif number is not None and not args.dry_run:
            created_issues += 1

        # Rate limiting between creations (skip after last issue and on dry-run)
        if not args.dry_run and index < len(issues):
            time.sleep(max(0.0, args.delay))

    print()
    print("== Summary ==")
    if args.dry_run:
        print(f"DRY-RUN complete. {len(issues)} issues would be processed.")
    else:
        print(f"Created: {created_issues} | Skipped (existing): {skipped_issues}")
        print(f"View: https://github.com/{repo}/milestones")
    return 0


if __name__ == "__main__":
    sys.exit(main())
