#!/usr/bin/env python3
"""
project_creator2.py

Modern Python project scaffolder.
Creates src-layout, tests, pyproject.toml, and initializes git.

Usage:
    python project_creator2.py my_lib --author "Jane Doe" --email "jane@example.com"
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import datetime
from pathlib import Path

MIT_LICENSE = """MIT License

Copyright (c) {year} {author}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

PYPROJECT_TEMPLATE = """[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{package}"
version = "0.1.0"
description = "{description}"
readme = "README.md"
requires-python = ">=3.9"
license = {{text = "MIT"}}
authors = [
    {{ name = "{author}", email = "{email}" }}
]

[project.optional-dependencies]
dev = ["black", "isort", "pytest", "mypy"]

[tool.setuptools.packages.find]
where = ["src"]

[tool.black]
line-length = 88
target-version = ['py39']
"""

README_TEMPLATE = """# {package}

{description}

## Installation

```bash
pip install -e .
```

## Usage

```python
from {package} import __version__
print(__version__)
```

## Development

```bash
pytest
black .
isort .
```
"""

GITIGNORE = """# Byte-compiled
__pycache__/
*.py[cod]

# Virtual env
venv/
.env

# Testing
.pytest_cache/
.coverage

# Build
dist/
build/
*.egg-info/
"""

def check_git_available() -> bool:
    try:
        subprocess.run(["git", "--version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def create_project(name: str, author: str, email: str, description: str) -> None:
    root = Path(name).resolve()
    if root.exists():
        print(f"Error: Directory '{name}' already exists.")
        sys.exit(1)

    pkg_name = name.replace("-", "_")
    src_dir = root / "src" / pkg_name
    tests_dir = root / "tests"

    src_dir.mkdir(parents=True)
    tests_dir.mkdir(parents=True)

    (src_dir / "__init__.py").write_text(f'"""{description}"""
__version__ = "0.1.0"
', encoding='utf-8')
    (root / "README.md").write_text(README_TEMPLATE.format(package=pkg_name, description=description), encoding='utf-8')
    (root / "LICENSE").write_text(MIT_LICENSE.format(year=datetime.datetime.now().year, author=author), encoding='utf-8')
    (root / ".gitignore").write_text(GITIGNORE, encoding='utf-8')
    (root / "pyproject.toml").write_text(
        PYPROJECT_TEMPLATE.format(package=pkg_name, author=author, email=email, description=description),
        encoding='utf-8'
    )

    (tests_dir / "test_placeholder.py").write_text("""def test_dummy():
    assert True
""", encoding='utf-8')

    if check_git_available():
        print(f"Initializing git repository in {root}...")
        subprocess.run(["git", "init", str(root)], check=False)
    else:
        print("Warning: git is not available, skipping git initialization.")

    print(f"Project '{name}' created successfully.")
    print(f"  cd {name}")
    print("  python -m venv venv")
    print("  source venv/bin/activate  # on Unix/macOS")
    print("  .\venv\Scripts\activate  # on Windows")
    print("  pip install -e .")


def main() -> None:
    parser = argparse.ArgumentParser(description="Project Creator")
    parser.add_argument("name", help="Project name")
    parser.add_argument("-a", "--author", required=True, help="Author name")
    parser.add_argument("-e", "--email", required=True, help="Author email")
    parser.add_argument("-d", "--description", default="A new Python project", help="Description")

    args = parser.parse_args()
    create_project(args.name, args.author, args.email, args.description)


if __name__ == "__main__":
    main()
