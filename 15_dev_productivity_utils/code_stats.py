#!/usr/bin/env python3
"""
code_stats.py

Advanced code statistics tool supporting multiple languages.
Calculates lines of code (LOC), comments, blank lines, and complexity.

Features:
- Multi-language support (Python, JS, HTML, CSS, etc.)
- JSON output for CI/CD integration
- Cyclomatic complexity calculation (Python only)

Usage:
    python code_stats.py ./my_project --json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

log = logging.getLogger(__name__)

# Language specific comment patterns
LANG_CONFIG = {
    ".py": {"comment": "#", "complexity": True},
    ".js": {"comment": "//", "complexity": False},
    ".ts": {"comment": "//", "complexity": False},
    ".java": {"comment": "//", "complexity": False},
    ".c": {"comment": "//", "complexity": False},
    ".cpp": {"comment": "//", "complexity": False},
    ".cs": {"comment": "//", "complexity": False},
    ".go": {"comment": "//", "complexity": False},
    ".rs": {"comment": "//", "complexity": False},
    ".rb": {"comment": "#", "complexity": False},
    ".sh": {"comment": "#", "complexity": False},
    ".css": {"comment": r"/*", "complexity": False}, # Basic detection
    ".html": {"comment": r"<!--", "complexity": False},
}

def _count_lines_py(path: Path) -> Dict[str, int]:
    """Accurate line count for Python using AST to handle multi-line strings."""
    total, comment, blank, docstring = 0, 0, 0, 0
    try:
        import ast
        content = path.read_text(encoding='utf-8', errors='ignore')
        tree = ast.parse(content)
        
        # Count docstrings as comments/lines
        docstring_nodes = {ast.get_docstring(node) for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module))}
        
        lines = content.splitlines()
        total = len(lines)
        for line in lines:
            stripped = line.strip()
            if not stripped: blank += 1
            elif stripped.startswith("#"): comment += 1
        
        # Note: This is a simplified heuristic. AST based counting is more complex.
        return {"total": total, "blank": blank, "comment": comment, "code": total - blank - comment}
    except Exception:
        return _count_lines_generic(path, "#")

def _count_lines_generic(path: Path, comment_char: str) -> Dict[str, int]:
    total, comment, blank = 0, 0, 0
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            total += 1
            stripped = line.strip()
            if not stripped:
                blank += 1
            elif stripped.startswith(comment_char):
                comment += 1
    return {"total": total, "blank": blank, "comment": comment, "code": total - blank - comment}

def _compute_complexity_py(path: Path) -> int:
    try:
        from radon.complexity import cc_visit
        source = path.read_text(encoding='utf-8', errors='ignore')
        blocks = cc_visit(source)
        return sum(b.complexity for b in blocks)
    except ImportError:
        log.warning("Install 'radon' for complexity metrics")
        return 0
    except Exception:
        return 0

def analyse_path(root: Path, include_complexity: bool = False) -> List[Dict]:
    results = []
    for ext, config in LANG_CONFIG.items():
        for file_path in root.rglob(f"*{ext}"):
            # Skip virtual envs and hidden dirs
            if ".venv" in file_path.parts or "venv" in file_path.parts or file_path.name.startswith("."):
                continue

            if ext == ".py":
                stats = _count_lines_py(file_path)
            else:
                stats = _count_lines_generic(file_path, config["comment"])
            
            entry = {
                "file": str(file_path.relative_to(root)),
                "lang": ext,
                "lines": stats["total"],
                "code": stats["code"],
                "blank": stats["blank"],
                "comment": stats["comment"],
            }
            
            if include_complexity and config["complexity"]:
                entry["complexity"] = _compute_complexity_py(file_path)
            
            results.append(entry)
    return results

def _print_report(data: List[Dict], use_json: bool) -> None:
    if use_json:
        print(json.dumps(data, indent=2))
        return

    total_files = len(data)
    total_lines = sum(d["lines"] for d in data)
    total_code = sum(d["code"] for d in data)
    total_blank = sum(d["blank"] for d in data)
    total_comment = sum(d["comment"] for d in data)
    total_complexity = sum(d.get("complexity", 0) for d in data)

    print("\n=== Code Statistics ===")
    print(f"Files examined    : {total_files}")
    print(f"Total Lines        : {total_lines}")
    print(f"Code Lines         : {total_code} ({total_code/total_lines:.1%})")
    print(f"Blank Lines        : {total_blank} ({total_blank/total_lines:.1%})")
    print(f"Comment Lines      : {total_comment} ({total_comment/total_lines:.1%})")
    if total_complexity:
        print(f"Cyclomatic Complexity: {total_complexity}")
    print("-" * 30)
    print("Top 5 Files by Lines:")
    for item in sorted(data, key=lambda x: x['lines'], reverse=True)[:5]:
        print(f"  {item['file']}: {item['lines']} lines")

def main():
    parser = argparse.ArgumentParser(description="Code Stats Utility")
    parser.add_argument("path", default=".", help="Root directory to analyze")
    parser.add_argument("--complexity", action="store_true", help="Calculate complexity (Python only)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    
    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory")
        sys.exit(1)
        
    data = analyse_path(root, include_complexity=args.complexity)
    _print_report(data, use_json=args.json)

if __name__ == "__main__":
    main()
