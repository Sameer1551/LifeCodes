#!/usr/bin/env python3
"""
formatter.py

Unified code formatter wrapper for Black and isort.
Ensures consistent code style and import sorting.

Usage:
    python formatter.py ./src --check
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import shutil
from pathlib import Path

DEFAULT_EXCLUDES = ".venv,venv,env,.git,node_modules,__pycache__,build,dist"

def check_tool(name: str):
    if not shutil.which(name):
        print(f"Error: '{name}' is not installed or not in PATH.")
        print(f"Run: pip install {name}")
        sys.exit(1)

def run_formatter(targets: list, check: bool = False, diff: bool = False):
    check_tool("isort")
    check_tool("black")
    
    cmd_args = []
    if check:
        cmd_args.append("--check")
    if diff:
        cmd_args.append("--diff")

    # 1. Sort Imports
    print("Running isort...")
    isort_cmd = ["isort"] + cmd_args + targets
    res = subprocess.run(isort_cmd)
    if res.returncode != 0 and check:
        print("Imports need sorting.", file=sys.stderr)
        # Continue to black to show all issues

    # 2. Format Code
    print("Running black...")
    black_cmd = ["black"] + cmd_args + targets
    res = subprocess.run(black_cmd)
    
    if res.returncode != 0:
        sys.exit(res.returncode)
    print("Code formatted successfully.")

def main():
    parser = argparse.ArgumentParser(description="Code Formatter (Black + Isort)")
    parser.add_argument("paths", nargs="+", help="Files or directories to format")
    parser.add_argument("--check", action="store_true", help="Check formatting without modifying files")
    parser.add_argument("--diff", action="store_true", help="Show diff of changes")
    
    args = parser.parse_args()
    
    # Convert paths to strings
    targets = [str(Path(p).resolve()) for p in args.paths]
    run_formatter(targets, check=args.check, diff=args.diff)

if __name__ == "__main__":
    main()
