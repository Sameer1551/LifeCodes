#!/usr/bin/env python3
"""
code_complexity_checker.py

Measures code complexity using AST-based heuristics
(decision density, nesting depth, function length).
Works on Python files. No external dependencies.

Usage:
    python code_complexity_checker.py ./src
    python code_complexity_checker.py ./src --threshold 15
    python code_complexity_checker.py ./src --report
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path
from typing import Optional


class ComplexityVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.functions: list[dict] = []
        self._depth = 0
        self._max_depth = 0
        self._decision_points = 0
        self._current_name = ""
        self._current_lines = (0, 0)
        self._suppress = False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._enter_function(node.name, node.lineno)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._enter_function(node.name, node.lineno)

    def _enter_function(self, name: str, lineno: int) -> None:
        if self._current_name:
            self._save_function()
        self._current_name = name
        self._current_lines = (lineno, lineno)
        self._depth = 0
        self._max_depth = 0
        self._decision_points = 0
        self._suppress = False

    def visit_For(self, node: ast.For) -> None:
        self._record_decision()
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self._record_decision()
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        self._record_decision()
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try) -> None:
        self._record_decision()
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self._record_decision()
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        self._record_decision()
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        self._record_decision()
        self.generic_visit(node)

    def _record_decision(self) -> None:
        self._depth += 1
        self._decision_points += 1
        if self._depth > self._max_depth:
            self._max_depth = self._depth

    def _save_function(self) -> None:
        if self._current_name:
            end_lineno = self._current_lines[1]
            lines = end_lineno - self._current_lines[0] + 1
            complexity = self._decision_points + self._max_depth
            self.functions.append({
                "name": self._current_name,
                "lines": lines,
                "complexity": complexity,
                "decisions": self._decision_points,
                "nesting": self._max_depth,
            })


def _analyze_file(path: Path, threshold: int = 15) -> list[dict]:
    try:
        source = path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source, filename=str(path))
    except (SyntaxError, ValueError):
        return []

    funcs: list[dict] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_data = _measure_function(node)
            if func_data["complexity"] >= threshold:
                func_data["file"] = str(path.name)
                funcs.append(func_data)

    return funcs


def _measure_function(node: ast.FunctionDef) -> dict:
    decision_points = 0
    max_depth = 0
    depth = 0

    def _walk(n: ast.AST) -> None:
        nonlocal decision_points, max_depth, depth
        if isinstance(n, (ast.For, ast.While, ast.If, ast.Try, ast.ExceptHandler, ast.Assert, ast.With)):
            decision_points += 1
            depth += 1
            if depth > max_depth:
                max_depth = depth
        for child in ast.iter_child_nodes(n):
            _walk(child)
        if isinstance(n, (ast.For, ast.While, ast.If, ast.Try, ast.ExceptHandler, ast.Assert, ast.With)):
            depth -= 1

    _walk(node)
    complexity = decision_points + max_depth
    return {
        "name": node.name,
        "lines": node.end_lineno - node.lineno + 1 if node.end_lineno else 0,
        "complexity": complexity,
        "decisions": decision_points,
        "nesting": max_depth,
    }


def analyze(root: Path, threshold: int = 15, verbose: bool = False) -> tuple[list[dict], int, int]:
    all_funcs: list[dict] = []
    files_checked = 0

    for py_file in root.rglob("*.py"):
        if any(part.startswith(".") or part in (".venv", "venv", "env") for part in py_file.parts):
            continue
        funcs = _analyze_file(py_file, threshold)
        if funcs:
            for f in funcs:
                f["file"] = str(py_file.relative_to(root))
            all_funcs.extend(funcs)
        files_checked += 1

    return all_funcs, files_checked, len(all_funcs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Code Complexity Checker")
    parser.add_argument("path", default=".", help="Root directory or file")
    parser.add_argument("--threshold", type=int, default=15, help="Complexity threshold")
    parser.add_argument("--report", action="store_true", help="Detailed report")
    parser.add_argument("--files", action="store_true", help="Show file-level summary only")
    args = parser.parse_args()

    root = Path(args.path).resolve()
    if not root.exists():
        print(f"Error: '{root}' not found", file=sys.stderr)
        sys.exit(1)

    if root.is_file():
        funcs = _analyze_file(root, args.threshold)
        print(f"File: {root}")
        print(f"High complexity functions: {len(funcs)}")
        for f in funcs:
            print(f"  {f['name']}: complexity={f['complexity']}, lines={f['lines']}, nesting={f['nesting']}")
        return

    funcs, files_checked, flagged = analyze(root, args.threshold, args.report)
    print(f"Files checked: {files_checked}")
    print(f"Functions above threshold ({args.threshold}): {flagged}")

    if funcs:
        print("\n--- Top Complex Functions ---")
        for f in sorted(funcs, key=lambda x: x["complexity"], reverse=True)[:10]:
            print(f"  {f['file']}::{f['name']}: complexity={f['complexity']}, lines={f['lines']}")


if __name__ == "__main__":
    main()