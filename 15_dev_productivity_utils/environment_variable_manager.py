#!/usr/bin/env python3
"""
environment_variable_manager.py

Manages environment variables across platforms.
Load from .env files, set in shell profiles, list, export, and validate.
Supports cross-platform usage (Windows, Linux, macOS).

Usage:
    python environment_variable_manager.py load
    python environment_variable_manager.py load --path .env
    python environment_variable_manager.py set MY_VAR hello
    python environment_variable_manager.py list
    python environment_variable_manager.py export MY_VAR NEW_VAL
    python environment_variable_manager.py validate
    python environment_variable_manager.py export-shell > env_setup.sh
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

ENV_RE = re.compile(r"^([A-Z_][A-Z0-9_]*)\s*=\s*(.*)$", re.MULTILINE)


def load_env_file(path: Path) -> dict[str, str]:
    vars_: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = ENV_RE.match(line.strip())
        if m:
            vars_[m.group(1)] = m.group(2).strip().strip("\"'")
    return vars_


def set_var(name: str, value: str, persistent: bool = True) -> None:
    os.environ[name] = value
    if persistent:
        if sys.platform == "win32":
            subprocess.run(["setx", name, value], check=False)
        else:
            shell_rc = Path.home() / ".bashrc"
            if os.getenv("ZSH_VERSION"):
                shell_rc = Path.home() / ".zshrc"
            entry = f'\nexport {name}="{value}"\n'
            current = shell_rc.read_text(encoding="utf-8", errors="ignore")
            if f'export {name}=' not in current:
                shell_rc.write_text(current + entry, encoding="utf-8")
    print(f"Set {name}={value}")


def list_vars(prefix: Optional[str] = None, file_path: Optional[Path] = None) -> None:
    if file_path:
        vars_ = load_env_file(file_path)
    else:
        vars_ = dict(os.environ)

    if prefix:
        vars_ = {k: v for k, v in vars_.items() if k.startswith(prefix.upper())}

    print(f"Environment variables ({len(vars_)}):")
    for k, v in sorted(vars_.items()):
        masked = v[:4] + "***" if len(v) > 4 else "***"
        print(f"  {k}={masked}")


REQUIRED_PATTERNS = {
    "PATH": r"^[^\n]*$",
    "HOME": r"^.",
    "USER": r"^.",
    "SHELL": r"^.",
    "TERM": r"^.",
    "PYTHONPATH": r"^.",
}


def validate(required_vars: Optional[list[str]] = None) -> int:
    missing: list[str] = []
    for var in (required_vars or list(REQUIRED_PATTERNS.keys())):
        if var not in os.environ:
            missing.append(var)

    if missing:
        print(f"Missing variables: {', '.join(missing)}", file=sys.stderr)
        return 1
    print("All required variables present.")
    return 0


def export_shell(shell_type: Optional[str] = None) -> None:
    if not shell_type:
        shell_type = "bash"
        if sys.platform == "win32":
            shell_type = "powershell"
        elif os.getenv("ZSH_VERSION"):
            shell_type = "zsh"

    if shell_type == "bash":
        print("# Add to ~/.bashrc")
        print(f'export PATH="{os.getenv("PATH", "")}"')
    elif shell_type == "zsh":
        print("# Add to ~/.zshrc")
        print(f'export PATH="{os.getenv("PATH", "")}"')
    elif shell_type == "powershell":
        print("# Add to $PROFILE")
        print(f'$env:PATH = "{os.getenv("PATH", "")}"')
    elif shell_type == "fish":
        print("# Add to ~/.config/fish/config.fish")
        print(f'set -x PATH "{os.getenv("PATH", "")}"')


def main() -> None:
    parser = argparse.ArgumentParser(description="Environment Variable Manager")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub_load = sub.add_parser("load", help="Load .env file into current session")
    sub_load.add_argument("--path", default=".env", help=".env file path")

    sub_set = sub.add_parser("set", help="Set an environment variable")
    sub_set.add_argument("name", help="Variable name")
    sub_set.add_argument("value", help="Variable value")
    sub_set.add_argument("--session", action="store_true", help="Set only for current session (no persistence)")

    sub_list = sub.add_parser("list", help="List environment variables")
    sub_list.add_argument("--prefix", help="Filter by prefix")
    sub_list.add_argument("--file", help="Read from .env file instead")

    sub_export = sub.add_parser("export", help="Export variable with new value")
    sub_export.add_argument("name", help="Variable name")
    sub_export.add_argument("value", help="New value")

    sub_validate = sub.add_parser("validate", help="Validate required variables")
    sub_validate.add_argument("--vars", help="Comma-separated variable names")

    sub_shell = sub.add_parser("export-shell", help="Export shell setup script")
    sub_shell.add_argument("--shell", choices=["bash", "zsh", "powershell", "fish"], help="Shell type")

    args = parser.parse_args()

    if args.cmd == "load":
        vars_ = load_env_file(Path(args.path))
        os.environ.update(vars_)
        print(f"Loaded {len(vars_)} variables from {args.path}")
    elif args.cmd == "set":
        set_var(args.name, args.value, persistent=not getattr(args, "session", False))
    elif args.cmd == "list":
        list_vars(prefix=getattr(args, "prefix", None), file_path=Path(args.file) if hasattr(args, "file") and args.file else None)
    elif args.cmd == "export":
        os.environ[args.name] = args.value
        print(f"{args.name}={args.value}")
    elif args.cmd == "validate":
        vars_list = args.vars.split(",") if args.vars else None
        sys.exit(validate(required_vars=vars_list))
    elif args.cmd == "export-shell":
        export_shell(shell_type=getattr(args, "shell", None))


if __name__ == "__main__":
    main()