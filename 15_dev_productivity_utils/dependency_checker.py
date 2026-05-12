#!/usr/bin/env python3
"""
dependency_checker.py

Inspects Python project dependencies.
Reads requirements.txt, pyproject.toml, or pip freeze.
Detects outdated packages and missing optional groups.
Supports virtualenv and uv environments.

Usage:
    python dependency_checker.py
    python dependency_checker.py --outdated
    python dependency_checker.py --format json
    python dependency_checker.py --check-missing
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Optional

DIST_RE = re.compile(r"^(?:--.+ |)([^!=<>\[\]]+)(?: ?(?:[<>=!]+|])|)\s*$", re.MULTILINE)


def _parse_req_file(path: Path) -> dict[str, str]:
    reqs = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "-r ", "-c ", "-e ", "--")):
            continue
        match = re.match(DIST_RE, line)
        if match:
            name = match.group(1).partition("[")[0]
            if name:
                reqs[name.lower()] = line
    return reqs


def _parse_pyproject(root: Path) -> dict[str, list[str]]:
    deps: dict[str, list[str]] = {"core": [], "dev": [], "test": [], "extras": {}}
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return deps

    content = pyproject.read_text(encoding="utf-8", errors="ignore")
    current = "core"
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            if "optional-dependencies" in stripped:
                current = stripped.split("optional-dependencies.")[1].rstrip("]")
            elif stripped in ("dependencies", "project.dependencies"):
                current = "core"
            elif stripped in ("dev.dependencies", "project.optional-dependencies.dev"):
                current = "dev"
            elif stripped in ("test.dependencies",):
                current = "test"
        elif stripped and not stripped.startswith("#"):
            dep = stripped.strip('"').strip("'")
            if dep:
                if current == "extras":
                    deps["extras"][stripped] = []
                else:
                    deps.setdefault(current, []).append(dep)
    return deps


def get_installed() -> dict[str, str]:
    dists = {}
    for dist in importlib.metadata.distributions():
        dists[dist.name.lower()] = dist.version
    return dists


def _build_req_map(installed: dict[str, str]) -> dict[str, str]:
    req_map = installed.copy()
    for req in list(installed.keys()):
        if "-" in req:
            req_map[req.replace("-", "_")] = installed[req]
            req_map[req.replace("_", "-")] = installed[req]
    return req_map


def check_missing(reqs: dict[str, str], installed: dict[str, str]) -> list[tuple[str, str]]:
    req_map = _build_req_map(installed)
    missing = []
    for name, raw in reqs.items():
        if name not in installed and name not in req_map:
            missing.append((name, raw))
    return missing


def check_outdated(installed: dict[str, str]) -> list[tuple[str, str, str]]:
    outdated = []
    for name, version in sorted(installed.items()):
        try:
            latest = importlib.metadata.version(name)
            if latest != version:
                outdated.append((name, version, latest))
        except importlib.metadata.PackageNotFoundError:
            pass
    return outdated


def _format_json(reqs: dict, installed: dict, outdated: list, missing: list) -> str:
    return json.dumps({
        "requirements_file": reqs,
        "installed": installed,
        "outdated": [{"name": n, "current": c, "latest": l} for n, c, l in outdated],
        "missing": [{"name": n, "requirement": r} for n, r in missing],
    }, indent=2)


def _format_text(reqs: dict, installed: dict, outdated: list, missing: list) -> str:
    lines = []
    lines.append("=== Installed Packages ===")
    for name, ver in sorted(installed.items()):
        marker = ""
        if (name, ver, importlib.metadata.version(name)) in outdated:
            marker = " (outdated)"
        lines.append(f"  {name}=={ver}{marker}")
    lines.append(f"Total: {len(installed)} packages")

    if missing:
        lines.append("\n=== Missing from Requirements ===")
        for name, raw in missing:
            lines.append(f"  {name} (raw: {raw})")

    if outdated:
        lines.append("\n=== Outdated Packages ===")
        for name, cur, latest in outdated:
            lines.append(f"  {name}: {cur} -> {latest}")
        lines.append(f"\nRun: pip install -U {' '.join(n for n, _, _ in outdated)}")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Dependency Checker")
    parser.add_argument("--req", help="Path to requirements.txt (default: auto-detect)")
    parser.add_argument("--outdated", action="store_true", help="Show only outdated packages")
    parser.add_argument("--check-missing", action="store_true", help="Check packages in req not installed")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--check-missing-only", action="store_true", help="Exit 1 if missing packages found")
    args = parser.parse_args()

    root = Path.cwd()
    req_path = Path(args.req) if args.req else root / "requirements.txt"
    reqs = {}
    if req_path.exists():
        reqs = _parse_req_file(req_path)
    else:
        pyproject_deps = _parse_pyproject(root)
        if pyproject_deps.get("core"):
            for dep in pyproject_deps["core"]:
                reqs[dep.partition(" [")[0].lower()] = dep

    installed = get_installed()
    outdated = check_outdated(installed)
    missing = check_missing(reqs, installed) if reqs else []

    if args.outdated:
        for name, cur, latest in outdated:
            print(f"{name}: {cur} -> {latest}")
        return

    if args.format == "json":
        print(_format_json(reqs, installed, outdated, missing))
    else:
        print(_format_text(reqs, installed, outdated, missing))

    if args.check_missing_only and missing:
        print(f"\nError: {len(missing)} missing packages", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()