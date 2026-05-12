#!/usr/bin/env python3
"""
git_commit_analyzer.py

Analyzes git commit history.
Shows commits by author, file changes, frequency, and patterns.
Generalized — works on any git repository.

Usage:
    python git_commit_analyzer.py
    python git_commit_analyzer.py --path ./my_repo
    python git_commit_analyzer.py --authors
    python git_commit_analyzer.py --since "2024-01-01"
    python git_commit_analyzer.py --by-author
    python git_commit_analyzer.py --files
    python git_commit_analyzer.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional


GIT_COLOR_RE = re.compile(r"\x1b\[\d*m")


def _run_git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(cwd), "--no-pager"] + list(args),
        capture_output=True,
        text=True,
    )


def _parse_log_line(line: str) -> tuple[str, str, int, int, int]:
    parts = line.split("\x00")
    if len(parts) < 5:
        parts += [""] * (5 - len(parts))
    hash_, date_str, msg, insertions, deletions = parts[:5]
    files_changed = len(parts) - 5 if len(parts) > 5 else 0
    return hash_, date_str, msg, int(insertions or 0), int(deletions or 0)


def _parse_date(date_str: str) -> Optional[datetime]:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str[: len(fmt)], fmt)
        except ValueError:
            pass
    return None


def get_commits(
    repo: Path,
    since: Optional[str] = None,
    until: Optional[str] = None,
    author: Optional[str] = None,
    max_count: int = 500,
) -> list[dict]:
    range_arg = []
    if since:
        range_arg.append(f"--since={since}")
    if until:
        range_arg.append(f"--until={until}")

    author_arg = [f"--author={author}"] if author else []

    result = _run_git(
        repo,
        "log",
        f"--max-count={max_count}",
        "--format=%H%x00%aI%x00%B%x00%ai%x00%d%x00",
        "--shortstat",
        *range_arg,
        *author_arg,
    )
    if result.returncode != 0:
        print(f"Error: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)

    commits = []
    raw_entries = result.stdout.split("\x1e")
    for block in raw_entries:
        block = block.strip()
        if not block:
            continue
        parts = block.split("\n")
        if len(parts) < 2:
            continue
        header = parts[0]
        h_parts = header.split("\x00")
        if len(h_parts) < 3:
            continue
        hash_, date_str, msg = h_parts[0], h_parts[2], h_parts[1]

        insertions, deletions = 0, 0
        for stat_line in parts[1:]:
            stat_line = stat_line.strip()
            if stat_line.startswith("files changed"):
                files_changed = int(re.search(r"(\d+)", stat_line).group(1)) if re.search(r"(\d+)", stat_line) else 0
            elif stat_line.endswith("insertions"):
                insertions = sum(int(x) for x in re.findall(r"(\d+) insertion", stat_line))
            elif stat_line.endswith("deletions"):
                deletions = sum(int(x) for x in re.findall(r"(\d+) deletion", stat_line))

        dt = _parse_date(date_str)
        commits.append({
            "hash": hash_[:8],
            "date": date_str,
            "message": msg.strip(),
            "insertions": insertions,
            "deletions": deletions,
            "timestamp": dt.isoformat() if dt else None,
        })
    return commits


def _analyze_by_author(commits: list[dict]) -> dict:
    by_author: dict = defaultdict(lambda: {"commits": 0, "insertions": 0, "deletions": 0})
    result = _run_git(Path.cwd(), "shortlog", "-sne", "--format=%aN (%d)")
    if result.returncode == 0:
        for line in result.stdout.splitlines():
            parts = line.strip().split(maxsplit=1)
            if len(parts) == 2:
                count, name = parts
                name = GIT_COLOR_RE.sub("", name).strip()
                by_author[name] = {"commits": int(count), "insertions": 0, "deletions": 0}
    return by_author


def _analyze_by_file(repo: Path) -> list[tuple[str, int, int]]:
    result = _run_git(repo, "log", "--format=", "--numstat", "--log-size")
    file_stats: dict = defaultdict(lambda: [0, 0])
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            try:
                ins = int(parts[0]) if parts[0] != "-" else 0
                dels = int(parts[1]) if parts[1] != "-" else 0
                path = parts[2]
                file_stats[path] = [file_stats[path][0] + ins, file_stats[path][1] + dels]
            except ValueError:
                pass
    return sorted(file_stats.items(), key=lambda x: x[1][0] + x[1][1], reverse=True)


def _format_text(repo: Path, commits: list[dict], by_author: dict, by_file: list, use_json: bool) -> str:
    if use_json:
        return json.dumps({"commits": commits, "by_author": by_author, "by_file": by_file[:20]}, indent=2)

    lines = ["=== Git Commit Analysis ===", f"Total commits: {len(commits)}"]
    total_ins = sum(c["insertions"] for c in commits)
    total_dels = sum(c["deletions"] for c in commits)
    lines.append(f"Total insertions: {total_ins}")
    lines.append(f"Total deletions: {total_dels}")

    if by_author:
        lines.append("\n--- Top Authors ---")
        for name, stats in sorted(by_author.items(), key=lambda x: x[1]["commits"], reverse=True)[:10]:
            lines.append(f"  {name}: {stats['commits']} commits")

    if by_file[:5]:
        lines.append("\n--- Most Changed Files ---")
        for path, (ins, dels) in by_file[:5]:
            lines.append(f"  {path}: +{ins} -{dels}")

    lines.append("\n--- Recent Commits ---")
    for c in commits[:10]:
        lines.append(f"  [{c['hash']}] {c['message']} ({c['date']})")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Git Commit Analyzer")
    parser.add_argument("--path", default=".", help="Repository path")
    parser.add_argument("--since", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--until", help="End date (YYYY-MM-DD)")
    parser.add_argument("--author", help="Filter by author")
    parser.add_argument("--max", type=int, default=500, help="Max commits to analyze")
    parser.add_argument("--authors", action="store_true", help="Show top authors")
    parser.add_argument("--files", action="store_true", help="Show most changed files")
    parser.add_argument("--by-author", action="store_true", help="Detailed per-author stats")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    repo = Path(args.path).resolve()
    if not (repo / ".git").exists():
        print(f"Error: '{repo}' is not a git repository.", file=sys.stderr)
        sys.exit(1)

    commits = get_commits(repo, since=args.since, until=args.until, author=args.author, max_count=args.max)
    by_author = _analyze_by_author(commits) if args.by_author else {}
    by_file = _analyze_by_file(repo) if args.files else []
    output = _format_text(repo, commits, by_author, by_file, args.json)
    print(output)


if __name__ == "__main__":
    main()