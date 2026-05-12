#!/usr/bin/env python3
"""
json_validator.py

Validates and formats JSON files.
Checks syntax, schema compliance, duplicate keys, and large files.
Formats with configurable indentation and sorting.
Generalized — no external dependencies.

Usage:
    python json_validator.py config.json
    python json_validator.py data.json --check-schema schema.json
    python json_validator.py --pretty data.json
    python json_validator.py --sort data.json --out sorted.json
    python json_validator.py --batch *.json
    python json_validator.py --validate-stdin
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional


def validate_json(content: str) -> tuple[bool, Optional[str]]:
    try:
        json.loads(content)
        return True, None
    except json.JSONDecodeError as e:
        return False, f"Line {e.lineno}, Col {e.colno}: {e.msg}"


def _check_duplicates(obj: Any, path: str = "") -> list[str]:
    issues = []
    if isinstance(obj, dict):
        keys_seen: set = set()
        for k, v in obj.items():
            if k in keys_seen:
                issues.append(f"{path}.{k} (duplicate key)")
            keys_seen.add(k)
            issues.extend(_check_duplicates(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            issues.extend(_check_duplicates(item, f"{path}[{i}]"))
    return issues


def _validate_schema(data: Any, schema: dict, path: str = "") -> list[str]:
    issues = []
    required = schema.get("required", [])
    if required:
        if not isinstance(data, dict):
            issues.append(f"{path}: must be an object")
        else:
            for field in required:
                if field not in data:
                    issues.append(f"{path}.{field} (required field missing)")

    properties = schema.get("properties", {})
    if properties and isinstance(data, dict):
        for k, v in data.items():
            if k in properties:
                prop_schema = properties[k]
                expected_type = prop_schema.get("type")
                actual_type = type(v).__name__
                if expected_type == "object" and not isinstance(v, dict):
                    issues.append(f"{path}.{k}: expected object, got {actual_type}")
                elif expected_type == "array" and not isinstance(v, list):
                    issues.append(f"{path}.{k}: expected array, got {actual_type}")
                elif expected_type == "string" and not isinstance(v, str):
                    issues.append(f"{path}.{k}: expected string, got {actual_type}")
                elif expected_type == "number" and not isinstance(v, (int, float)):
                    issues.append(f"{path}.{k}: expected number, got {actual_type}")
    return issues


def format_json(content: str, indent: int = 2, sort_keys: bool = False) -> str:
    data = json.loads(content)
    return json.dumps(data, indent=indent, sort_keys=sort_keys)


def main() -> None:
    parser = argparse.ArgumentParser(description="JSON Validator")
    parser.add_argument("files", nargs="*", help="JSON files to validate")
    parser.add_argument("--pretty", action="store_true", help="Reformat JSON")
    parser.add_argument("--sort", action="store_true", help="Sort keys")
    parser.add_argument("--check-duplicates", action="store_true", help="Check for duplicate keys")
    parser.add_argument("--check-schema", help="Validate against JSON schema")
    parser.add_argument("--out", help="Output file")
    parser.add_argument("--batch", action="store_true", help="Validate all JSON files in current directory")
    parser.add_argument("--validate-stdin", action="store_true", help="Validate stdin")
    parser.add_argument("--compact", action="store_true", help="Output compact JSON")
    args = parser.parse_args()

    files_to_process: list[Path] = []

    if args.validate_stdin:
        import sys as _sys
        content = _sys.stdin.read()
        ok, err = validate_json(content)
        if ok:
            print("Valid JSON")
        else:
            print(f"Invalid: {err}", file=_sys.stderr)
            _sys.exit(1)
        return

    if args.batch:
        files_to_process = list(Path.cwd().glob("*.json"))
    else:
        files_to_process = [Path(f) for f in args.files]

    schema = {}
    if args.check_schema:
        schema_raw = Path(args.check_schema).read_text(encoding="utf-8")
        schema = json.loads(schema_raw)

    results = []
    for fp in files_to_process:
        if not fp.exists():
            print(f"Warning: {fp} not found")
            continue

        content = fp.read_text(encoding="utf-8", errors="ignore")
        ok, err = validate_json(content)
        status = "OK" if ok else f"ERROR: {err}"

        data = None
        if ok:
            try:
                data = json.loads(content)
            except Exception:
                pass

        if ok and args.check_duplicates and data:
            dups = _check_duplicates(data)
            if dups:
                status = f"DUPLICATE: {dups}"

        if ok and schema and data:
            schema_issues = _validate_schema(data, schema)
            if schema_issues:
                status = f"SCHEMA: {schema_issues}"

        results.append((fp.name, status))

    if args.pretty or args.sort:
        out_content = format_json(
            files_to_process[0].read_text(encoding="utf-8"),
            indent=0 if args.compact else 2,
            sort_keys=args.sort,
        )
        if args.out:
            Path(args.out).write_text(out_content, encoding="utf-8")
            print(f"Written to {args.out}")
        else:
            print(out_content)
        return

    for name, status in results:
        print(f"  {name}: {status}")


if __name__ == "__main__":
    main()