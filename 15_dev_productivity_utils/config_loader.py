#!/usr/bin/env python3
"""
config_loader.py

Loads and merges configuration from YAML, TOML, JSON, and .env files.
Supports environment-specific overrides, secret masking, and dotenv
loading. Works cross-platform.

Usage:
    python config_loader.py config.yaml
    python config_loader.py config.toml --env production
    python config_loader.py config.json --env staging --secrets
    python config_loader.py config.yaml --get database.host
    python config_loader.py --defaults db=localhost port=5432
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional

try:
    import tomllib
    HAS_TOMLLIB = True
except ImportError:
    HAS_TOMLLIB = False

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def _load_yaml(path: Path) -> dict:
    if not HAS_YAML:
        raise ImportError("PyYAML not installed. Run: pip install pyyaml")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _load_toml(path: Path) -> dict:
    if not HAS_TOMLLIB:
        try:
            import tomli
            return tomli.loads(path.read_text(encoding="utf-8"))
        except ImportError:
            raise ImportError("tomli not installed. Run: pip install tomli")
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


ENV_RE = re.compile(r"^([A-Z_][A-Z0-9_]*)\s*=\s*(.*)$", re.MULTILINE)


def _load_env_file(path: Path) -> dict[str, str]:
    env_vars = {}
    content = path.read_text(encoding="utf-8", errors="ignore")
    for m in ENV_RE.finditer(content):
        key, val = m.group(1), m.group(2).strip()
        val = val.strip("\"'")
        env_vars[key] = val
    return env_vars


def _load_env_dir(path: Path) -> None:
    for env_file in [".env", ".env.local"]:
        env_path = path.parent / env_file
        if env_path.exists():
            loaded = _load_env_file(env_path)
            for k, v in loaded.items():
                os.environ[k] = v


def load(path: Path, env: Optional[str] = None, auto_env: bool = True) -> dict[str, Any]:
    suffix = path.suffix.lower()

    if suffix in (".yaml", ".yml"):
        data = _load_yaml(path)
    elif suffix == ".toml":
        data = _load_toml(path)
    elif suffix == ".json":
        data = _load_json(path)
    elif suffix == ".env":
        data = _load_env_file(path)
        if auto_env:
            os.environ.update(data)
        return data
    else:
        raise ValueError(f"Unsupported config format: {suffix}")

    if auto_env:
        _load_env_dir(path)

    if env:
        env_overrides = data.get("environments", {}).get(env, {})
        if isinstance(env_overrides, dict):
            merged = _deep_merge(data.get("defaults", data), env_overrides)
            return merged

    return data


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and k in result and isinstance(result[k], dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def get(d: dict, key: str, default: Any = None) -> Any:
    keys = key.split(".")
    val = d
    for k in keys:
        if isinstance(val, dict) and k in val:
            val = val[k]
        else:
            return default
    return val


SECRET_RE = re.compile(r"(api_key|password|secret|token|credential)\s*=\s*([^\s,}]+)", re.IGNORECASE)


def _mask_secrets(data: dict, depth: int = 0) -> dict:
    if depth > 10:
        return data
    result = {}
    for k, v in data.items():
        if isinstance(v, dict):
            result[k] = _mask_secrets(v, depth + 1)
        elif isinstance(v, str) and SECRET_RE.search(f"{k}={v}"):
            result[k] = "***MASKED***"
        else:
            result[k] = v
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Config Loader")
    parser.add_argument("file", nargs="?", help="Config file path")
    parser.add_argument("--env", help="Environment name")
    parser.add_argument("--get", dest="key", help="Dot-notation key to retrieve")
    parser.add_argument("--defaults", help="Default key=value pairs, comma-separated")
    parser.add_argument("--secrets", action="store_true", help="Mask secret values")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    defaults: dict = {}
    if args.defaults:
        for pair in args.defaults.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                defaults[k.strip()] = v.strip()

    data: dict = {}
    if args.file:
        path = Path(args.file).resolve()
        if not path.exists():
            print(f"Error: '{args.file}' not found", file=sys.stderr)
            sys.exit(1)
        data = load(path, env=args.env)

    data = _deep_merge(defaults, data)

    if args.secrets:
        data = _mask_secrets(data)

    if args.key:
        val = get(data, args.key)
        print(val if val is not None else "")
    elif args.json:
        print(json.dumps(data, indent=2, default=str))
    else:
        for k, v in data.items():
            print(f"{k}={v}")


if __name__ == "__main__":
    main()