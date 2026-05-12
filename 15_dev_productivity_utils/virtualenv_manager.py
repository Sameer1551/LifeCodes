#!/usr/bin/env python3
"""
virtualenv_manager.py

Manages Python virtual environments (venv, virtualenv).
Create, activate, install packages, and run commands inside a venv.
Works across Windows, Linux, and macOS.

Usage:
    python virtualenv_manager.py create myenv
    python virtualenv_manager.py create myenv --python python3.11
    python virtualenv_manager.py install myenv requests pandas
    python virtualenv_manager.py run myenv python script.py
    python virtualenv_manager.py list
    python virtualenv_manager.py freeze myenv
    python virtualenv_manager.py delete myenv
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import shutil
from pathlib import Path
from typing import Optional


def _sys_executable() -> str:
    return sys.executable


def _venv_executable(venv_path: Path, name: str) -> Path:
    if sys.platform == "win32":
        return venv_path / "Scripts" / f"{name}.exe"
    return venv_path / "bin" / name


def _activate_script(venv_path: Path) -> str:
    if sys.platform == "win32":
        return str(venv_path / "Scripts" / "Activate.ps1")
    return str(venv_path / "bin" / "activate")


def _is_venv(path: Path) -> bool:
    return (path / "pyvenv.cfg").exists() or (path / "Scripts" / "Activate.ps1").exists()


def create(name: str, python: Optional[str] = None) -> None:
    venv_path = Path(name).resolve()
    if venv_path.exists():
        print(f"Error: '{name}' already exists. Delete it first.")
        sys.exit(1)

    py_exec = python or _sys_executable()
    print(f"Creating venv '{name}' with {py_exec}...")
    result = subprocess.run([py_exec, "-m", "venv", str(venv_path)], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error creating venv: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    print(f"Done. Activate with:")
    if sys.platform == "win32":
        print(f"  .\\{name}\\Scripts\\Activate.ps1")
    else:
        print(f"  source {name}/bin/activate")
    print(f"Or use directly:")
    print(f"  {venv_path / 'bin' / 'python'} script.py")


def install(name: str, packages: list[str]) -> None:
    venv_path = Path(name).resolve()
    if not _is_venv(venv_path):
        print(f"Error: '{name}' is not a valid venv.", file=sys.stderr)
        sys.exit(1)

    py_exec = _venv_executable(venv_path, "python")
    print(f"Installing {packages} into '{name}'...")
    result = subprocess.run([str(py_exec), "-m", "pip", "install", "--upgrade", "pip"] + packages, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    print("Done.")


def run(name: str, script: str, args: list[str]) -> None:
    venv_path = Path(name).resolve()
    if not _is_venv(venv_path):
        print(f"Error: '{name}' is not a valid venv.", file=sys.stderr)
        sys.exit(1)

    py_exec = _venv_executable(venv_path, "python")
    result = subprocess.run([str(py_exec), str(Path(script).resolve())] + args, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    sys.exit(result.returncode)


def freeze(name: str) -> None:
    venv_path = Path(name).resolve()
    if not _is_venv(venv_path):
        print(f"Error: '{name}' is not a valid venv.", file=sys.stderr)
        sys.exit(1)

    py_exec = _venv_executable(venv_path, "python")
    result = subprocess.run([str(py_exec), "-m", "pip", "freeze"], capture_output=True, text=True)
    if result.returncode == 0:
        print(result.stdout, end="")
    else:
        print(f"Error: {result.stderr}", file=sys.stderr)
        sys.exit(1)


def list_venvs(search_dir: Optional[str] = None) -> None:
    root = Path(search_dir or ".").resolve()
    print("Virtual environments found:")
    found = False
    for item in root.rglob("pyvenv.cfg"):
        venv = item.parent
        print(f"  {venv}")
        found = True
    if not found:
        print("  (none)")


def delete(name: str) -> None:
    venv_path = Path(name).resolve()
    if not _is_venv(venv_path):
        print(f"Error: '{name}' is not a valid venv.", file=sys.stderr)
        sys.exit(1)
    import shutil as _s
    _s.rmtree(venv_path)
    print(f"Deleted '{name}'.")


def main() -> None:
    parser = argparse.ArgumentParser(description="VirtualEnv Manager")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub_create = sub.add_parser("create", help="Create a venv")
    sub_create.add_argument("name", help="Venv name")
    sub_create.add_argument("--python", help="Python interpreter (default: current)")

    sub_install = sub.add_parser("install", help="Install packages into venv")
    sub_install.add_argument("name", help="Venv name")
    sub_install.add_argument("packages", nargs="+", help="Package names")

    sub_run = sub.add_parser("run", help="Run script in venv")
    sub_run.add_argument("name", help="Venv name")
    sub_run.add_argument("script", help="Script to run")
    sub_run.add_argument("args", nargs="*", default=[], help="Script arguments")

    sub_freeze = sub.add_parser("freeze", help="Show installed packages")
    sub_freeze.add_argument("name", help="Venv name")

    sub_list = sub.add_parser("list", help="List venvs")
    sub_list.add_argument("dir", nargs="?", default=".", help="Search directory")

    sub_delete = sub.add_parser("delete", help="Delete a venv")
    sub_delete.add_argument("name", help="Venv name")

    args = parser.parse_args()

    if args.cmd == "create":
        create(args.name, getattr(args, "python", None))
    elif args.cmd == "install":
        install(args.name, args.packages)
    elif args.cmd == "run":
        run(args.name, args.script, args.args)
    elif args.cmd == "freeze":
        freeze(args.name)
    elif args.cmd == "list":
        list_venvs(getattr(args, "dir", None))
    elif args.cmd == "delete":
        delete(args.name)


if __name__ == "__main__":
    main()