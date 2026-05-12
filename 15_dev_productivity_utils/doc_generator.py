#!/usr/bin/env python3
"""
doc_generator.py

Generates a Markdown API reference from a Python package.
Extracts docstrings, type hints, and function signatures.

Usage:
    python doc_generator.py ./my_package --out docs/API.md
"""

from __future__ import annotations

import argparse
import ast
import logging
import sys
from pathlib import Path
from typing import List, Dict

log = logging.getLogger(__name__)

def _get_signature(node: ast.FunctionDef) -> str:
    """Extract function signature (args and return type)."""
    args = []
    for arg in node.args.args:
        arg_str = arg.arg
        if arg.annotation:
            arg_str += f": {ast.unparse(arg.annotation)}"
        args.append(arg_str)
    
    ret = ""
    if node.returns:
        ret = f" -> {ast.unparse(node.returns)}"
    
    return f"({', '.join(args)}){ret}"

def _extract_docs(file_path: Path) -> List[Dict]:
    source = file_path.read_text(encoding="utf-8", errors="ignore")
    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        log.warning(f"Could not parse {file_path}")
        return []

    items = []
    
    # Module doc
    mod_doc = ast.get_docstring(tree)
    if mod_doc:
        items.append({"type": "module", "name": file_path.stem, "doc": mod_doc, "sig": ""})

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            cls_doc = ast.get_docstring(node) or ""
            items.append({"type": "class", "name": node.name, "doc": cls_doc, "sig": ""})
            
            # Handle methods
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    meth_doc = ast.get_docstring(child) or ""
                    sig = _get_signature(child)
                    items.append({
                        "type": "method", 
                        "parent": node.name,
                        "name": child.name, 
                        "doc": meth_doc, 
                        "sig": sig
                    })

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_doc = ast.get_docstring(node) or ""
            sig = _get_signature(node)
            items.append({"type": "function", "name": node.name, "doc": func_doc, "sig": sig})
            
    return items

def generate_markdown(data: List[Dict]) -> str:
    lines = ["# API Reference\n"]
    
    # Table of Contents
    lines.append("## Table of Contents\n")
    for item in data:
        if item['type'] == 'class':
            lines.append(f"- [{item['name']}](#{item['name'].lower()})")
    lines.append("\n---\n")
    
    # Content
    current_class = None
    for item in data:
        if item['type'] == 'module':
            lines.append(f"## Module: {item['name']}\n")
            lines.append(f"{item['doc']}\n")
        elif item['type'] == 'class':
            lines.append(f"## Class: `{item['name']}`\n")
            lines.append(f"{item['doc']}\n")
            lines.append("### Methods\n")
            current_class = item['name']
        elif item['type'] == 'method':
            lines.append(f"#### `{item['name']}{item['sig']}`\n")
            lines.append(f"{item['doc']}\n")
        elif item['type'] == 'function':
            lines.append(f"## Function: `{item['name']}{item['sig']}`\n")
            lines.append(f"{item['doc']}\n")
            
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Doc Generator")
    parser.add_argument("package_path", help="Root directory of package")
    parser.add_argument("--out", default="API.md", help="Output markdown file")
    args = parser.parse_args()

    root = Path(args.package_path).resolve()
    if not root.is_dir():
        print("Error: Path does not exist")
        sys.exit(1)

    all_items = []
    for py_file in root.rglob("*.py"):
        all_items.extend(_extract_docs(py_file))

    md = generate_markdown(all_items)
    Path(args.out).write_text(md)
    print(f"Docs generated -> {args.out}")

if __name__ == "__main__":
    main()
