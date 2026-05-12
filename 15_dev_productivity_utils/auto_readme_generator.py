#!/usr/bin/env python3
"""
auto_readme_generator.py

Universal README generator for any project type.
Language-agnostic, platform-agnostic, and highly configurable.
Supports custom templates, multiple output formats, and extensible sections.

Usage:
    python auto_readme_generator.py
    python auto_readme_generator.py --config readme_config.json
    python auto_readme_generator.py --template custom_template.md
    python auto_readme_generator.py --output-format rst
    python auto_readme_generator.py --sections "intro,install,usage"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union


class ConfigLoader:
    """Loads configuration from various sources."""
    
    @staticmethod
    def load_json(path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            return {}

    @staticmethod
    def load_yaml(path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        try:
            import yaml
            return yaml.safe_load(path.read_text(encoding="utf-8", errors="ignore")) or {}
        except ImportError:
            return {}
        except Exception:
            return {}

    @staticmethod
    def load_toml(path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        try:
            import tomllib
            return tomllib.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except ImportError:
            try:
                import tomli
                return tomli.loads(path.read_text(encoding="utf-8", errors="ignore"))
            except ImportError:
                return {}
        except Exception:
            return {}

    @staticmethod
    def load_ini(path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        try:
            import configparser
            config = configparser.ConfigParser()
            config.read(path, encoding="utf-8")
            return {section: dict(config[section]) for section in config.sections()}
        except Exception:
            return {}

    @staticmethod
    def load_any(path: Path) -> Dict[str, Any]:
        suffix = path.suffix.lower()
        loaders = {
            ".json": ConfigLoader.load_json,
            ".yaml": ConfigLoader.load_yaml,
            ".yml": ConfigLoader.load_yaml,
            ".toml": ConfigLoader.load_toml,
            ".ini": ConfigLoader.load_ini,
            ".cfg": ConfigLoader.load_ini,
            ".conf": ConfigLoader.load_ini,
        }
        loader = loaders.get(suffix)
        if loader:
            return loader(path)
        return {}


class MetadataExtractor:
    """Extracts project metadata from various sources."""
    
    def __init__(self, root: Path):
        self.root = root
        self.config_files = [
            "package.json",
            "pyproject.toml",
            "setup.py",
            "setup.cfg",
            "Cargo.toml",
            "go.mod",
            "pom.xml",
            "build.gradle",
            "composer.json",
            "Gemfile",
            "requirements.txt",
            "package.xml",
            ".project",
            "project.clj",
            "mix.exs",
            "shard.yml",
        ]
    
    def extract_all(self) -> Dict[str, Any]:
        metadata = {
            "name": self.root.name,
            "version": "1.0.0",
            "description": "A project",
            "author": "",
            "email": "",
            "license": "MIT",
            "homepage": "",
            "repository": "",
            "keywords": [],
            "language": self._detect_language(),
            "package_manager": self._detect_package_manager(),
        }

        for config_file in self.config_files:
            config_path = self.root / config_file
            if config_path.exists():
                extracted = self._extract_from_file(config_path)
                metadata.update({k: v for k, v in extracted.items() if v})

        return metadata

    def _detect_language(self) -> str:
        language_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".java": "Java",
            ".go": "Go",
            ".rs": "Rust",
            ".rb": "Ruby",
            ".php": "PHP",
            ".cs": "C#",
            ".cpp": "C++",
            ".c": "C",
            ".kt": "Kotlin",
            ".swift": "Swift",
            ".scala": "Scala",
            ".clj": "Clojure",
            ".ex": "Elixir",
            ".dart": "Dart",
        }

        extensions = {}
        for file_path in self.root.rglob("*"):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                extensions[ext] = extensions.get(ext, 0) + 1

        if extensions:
            most_common = max(extensions.items(), key=lambda x: x[1])[0]
            return language_map.get(most_common, "Unknown")

        return "Unknown"

    def _detect_package_manager(self) -> str:
        manager_map = {
            "package.json": "npm",
            "yarn.lock": "yarn",
            "pnpm-lock.yaml": "pnpm",
            "requirements.txt": "pip",
            "pyproject.toml": "pip",
            "setup.py": "pip",
            "Cargo.toml": "cargo",
            "go.mod": "go",
            "pom.xml": "maven",
            "build.gradle": "gradle",
            "composer.json": "composer",
            "Gemfile": "bundler",
            "mix.exs": "hex",
            "shard.yml": "shards",
        }

        for config_file in self.config_files:
            if (self.root / config_file).exists():
                return manager_map.get(config_file, "unknown")

        return "unknown"

    def _extract_from_file(self, path: Path) -> Dict[str, Any]:
        suffix = path.suffix.lower()
        extractors = {
            ".json": self._extract_from_json,
            ".toml": self._extract_from_toml,
            ".yaml": self._extract_from_yaml,
            ".yml": self._extract_from_yaml,
            ".xml": self._extract_from_xml,
            ".gradle": self._extract_from_gradle,
            ".txt": self._extract_from_txt,
        }

        extractor = extractors.get(suffix)
        if extractor:
            return extractor(path)

        if path.name == "setup.py":
            return self._extract_from_setup_py(path)

        return {}

    def _extract_from_json(self, path: Path) -> Dict[str, Any]:
        data = ConfigLoader.load_json(path)
        return {
            "name": data.get("name", ""),
            "version": data.get("version", ""),
            "description": data.get("description", ""),
            "author": data.get("author", ""),
            "license": data.get("license", ""),
            "homepage": data.get("homepage", ""),
            "repository": data.get("repository", {}).get("url", ""),
            "keywords": data.get("keywords", []),
        }

    def _extract_from_toml(self, path: Path) -> Dict[str, Any]:
        data = ConfigLoader.load_toml(path)
        result = {}

        if "project" in data:
            project = data["project"]
            result.update({
                "name": project.get("name", ""),
                "version": project.get("version", ""),
                "description": project.get("description", ""),
                "license": str(project.get("license", {}).get("text", "")),
                "keywords": project.get("keywords", []),
            })

            authors = project.get("authors", [])
            if authors and isinstance(authors[0], dict):
                result["author"] = authors[0].get("name", "")
                result["email"] = authors[0].get("email", "")

        if "package" in data:
            package = data["package"]
            result.update({
                "name": package.get("name", ""),
                "version": package.get("version", ""),
                "description": package.get("description", ""),
                "authors": package.get("authors", []),
            })

        return result

    def _extract_from_yaml(self, path: Path) -> Dict[str, Any]:
        data = ConfigLoader.load_yaml(path)
        return {
            "name": data.get("name", ""),
            "version": data.get("version", ""),
            "description": data.get("description", ""),
            "author": data.get("author", ""),
            "license": data.get("license", ""),
        }

    def _extract_from_xml(self, path: Path) -> Dict[str, Any]:
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(path)
            root = tree.getroot()
            
            namespaces = {
                "maven": "http://maven.apache.org/POM/4.0.0",
            }

            def find_text(tag: str) -> str:
                elem = root.find(tag, namespaces)
                return elem.text if elem is not None else ""

            return {
                "name": find_text("maven:artifactId") or find_text("artifactId"),
                "version": find_text("maven:version") or find_text("version"),
                "description": find_text("maven:description") or find_text("description"),
            }
        except Exception:
            return {}

    def _extract_from_gradle(self, path: Path) -> Dict[str, Any]:
        content = path.read_text(encoding="utf-8", errors="ignore")
        result = {}

        name_match = re.search(r'name\s*[:=]\s*["\']([^"\']+)["\']', content)
        version_match = re.search(r'version\s*[:=]\s*["\']([^"\']+)["\']', content)
        description_match = re.search(r'description\s*[:=]\s*["\']([^"\']+)["\']', content)

        if name_match:
            result["name"] = name_match.group(1)
        if version_match:
            result["version"] = version_match.group(1)
        if description_match:
            result["description"] = description_match.group(1)

        return result

    def _extract_from_txt(self, path: Path) -> Dict[str, Any]:
        if path.name == "requirements.txt":
            return {"dependencies": self._parse_requirements(path)}
        return {}

    def _parse_requirements(self, path: Path) -> List[str]:
        deps = []
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line and not line.startswith(("#", "-r ", "-c ", "-e ", "--")):
                deps.append(line)
        return deps

    def _extract_from_setup_py(self, path: Path) -> Dict[str, Any]:
        try:
            import ast
            content = path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and hasattr(node.func, 'id') and node.func.id == 'setup':
                    kwargs = {}
                    for keyword in node.keywords:
                        if keyword.arg in ('name', 'version', 'description', 'author', 'author_email', 'license', 'url'):
                            if isinstance(keyword.value, ast.Constant):
                                kwargs[keyword.arg] = keyword.value.value
                            elif isinstance(keyword.value, ast.Str):
                                kwargs[keyword.arg] = keyword.value.s
                    return kwargs
        except Exception:
            pass
        return {}


class DependencyAnalyzer:
    """Analyzes project dependencies."""
    
    def __init__(self, root: Path):
        self.root = root
    
    def get_dependencies(self) -> Dict[str, List[str]]:
        dependencies = {
            "runtime": [],
            "development": [],
            "test": [],
        }

        dep_files = {
            "requirements.txt": "runtime",
            "requirements-dev.txt": "development",
            "dev-requirements.txt": "development",
            "test-requirements.txt": "test",
            "package.json": "runtime",
            "yarn.lock": "runtime",
            "pnpm-lock.yaml": "runtime",
            "go.mod": "runtime",
            "Cargo.toml": "runtime",
            "pom.xml": "runtime",
            "build.gradle": "runtime",
            "composer.json": "runtime",
            "Gemfile": "runtime",
        }

        for filename, dep_type in dep_files.items():
            file_path = self.root / filename
            if file_path.exists():
                deps = self._parse_dependency_file(file_path)
                dependencies[dep_type].extend(deps)

        return dependencies

    def _parse_dependency_file(self, path: Path) -> List[str]:
        suffix = path.suffix.lower()
        parsers = {
            ".txt": self._parse_txt_deps,
            ".json": self._parse_json_deps,
            ".toml": self._parse_toml_deps,
            ".xml": self._parse_xml_deps,
            ".gradle": self._parse_gradle_deps,
        }

        parser = parsers.get(suffix)
        if parser:
            return parser(path)

        if path.name in ("Gemfile", "go.mod"):
            return self._parse_line_based_deps(path)

        return []

    def _parse_txt_deps(self, path: Path) -> List[str]:
        deps = []
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line and not line.startswith(("#", "-r ", "-c ", "-e ", "--")):
                deps.append(line.split(">")[0].split("<")[0].split("=")[0].strip())
        return deps

    def _parse_json_deps(self, path: Path) -> List[str]:
        data = ConfigLoader.load_json(path)
        deps = []

        if "dependencies" in data:
            deps.extend(data["dependencies"].keys())
        if "devDependencies" in data:
            deps.extend(data["devDependencies"].keys())

        return deps

    def _parse_toml_deps(self, path: Path) -> List[str]:
        data = ConfigLoader.load_toml(path)
        deps = []

        if "dependencies" in data:
            deps.extend(data["dependencies"].keys())
        if "dev-dependencies" in data:
            deps.extend(data["dev-dependencies"].keys())

        return deps

    def _parse_xml_deps(self, path: Path) -> List[str]:
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(path)
            root = tree.getroot()
            deps = []

            for dep in root.findall(".//dependency"):
                group_id = dep.find("groupId")
                artifact_id = dep.find("artifactId")
                if group_id is not None and artifact_id is not None:
                    deps.append(f"{group_id.text}:{artifact_id.text}")

            return deps
        except Exception:
            return []

    def _parse_gradle_deps(self, path: Path) -> List[str]:
        content = path.read_text(encoding="utf-8", errors="ignore")
        deps = []

        for match in re.finditer(r'implementation\s+[\'"]([^:]+):([^:]+):([^\'"]+)[\'"]', content):
            deps.append(f"{match.group(1)}:{match.group(2)}")

        return deps

    def _parse_line_based_deps(self, path: Path) -> List[str]:
        deps = []
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                match = re.match(r'^\s*(\S+)', line)
                if match:
                    deps.append(match.group(1))
        return deps


class SectionGenerator:
    """Generates README sections."""
    
    def __init__(self, metadata: Dict[str, Any], dependencies: Dict[str, List[str]]):
        self.metadata = metadata
        self.dependencies = dependencies
    
    def generate_title(self) -> str:
        return f"# {self.metadata['name']}\n"
    
    def generate_description(self) -> str:
        return f"{self.metadata['description']}\n"
    
    def generate_badges(self, badge_config: Optional[Dict[str, Any]] = None) -> str:
        if not badge_config:
            return ""
        
        badges = []
        config = badge_config or {}
        
        if config.get("version", True) and self.metadata.get("version"):
            badges.append(f'[![Version](https://img.shields.io/badge/version-{self.metadata["version"]}-blue.svg)]')
        
        if config.get("license", True) and self.metadata.get("license"):
            license_badge = self.metadata["license"].replace(" ", "%20")
            badges.append(f'[![License](https://img.shields.io/badge/license-{license_badge}-green.svg)]')
        
        if config.get("language", True) and self.metadata.get("language"):
            lang_badge = self.metadata["language"].replace(" ", "%20")
            badges.append(f'[![Language](https://img.shields.io/badge/language-{lang_badge}-yellow.svg)]')
        
        if config.get("custom"):
            for badge in config["custom"]:
                badges.append(badge)
        
        return " ".join(badges) + "\n" if badges else ""
    
    def generate_installation(self) -> str:
        lines = ["## Installation", ""]
        
        pkg_manager = self.metadata.get("package_manager", "unknown")
        name = self.metadata.get("name", "your-project")
        
        install_commands = {
            "npm": f"npm install {name}",
            "yarn": f"yarn add {name}",
            "pnpm": f"pnpm add {name}",
            "pip": f"pip install {name}",
            "cargo": f"cargo install {name}",
            "go": f"go get {name}",
            "maven": f"mvn install",
            "gradle": f"./gradlew build",
            "composer": f"composer require {name}",
            "bundler": f"bundle install",
            "hex": f"mix deps.get",
            "shards": f"shards install",
        }
        
        if pkg_manager in install_commands:
            lines.append("```bash")
            lines.append(install_commands[pkg_manager])
            lines.append("```")
        else:
            lines.append("```bash")
            lines.append("# Add installation instructions for your package manager")
            lines.append("```")
        
        lines.append("")
        return "\n".join(lines)
    
    def generate_usage(self) -> str:
        lines = ["## Usage", ""]
        lines.append("```")
        lines.append("# Add usage examples here")
        lines.append("```")
        lines.append("")
        return "\n".join(lines)
    
    def generate_dependencies(self) -> str:
        lines = ["## Dependencies", ""]
        
        for dep_type, deps in self.dependencies.items():
            if deps:
                lines.append(f"### {dep_type.capitalize()}")
                lines.append("```")
                for dep in deps[:20]:
                    lines.append(dep)
                if len(deps) > 20:
                    lines.append(f"# ... and {len(deps) - 20} more")
                lines.append("```")
                lines.append("")
        
        return "\n".join(lines)
    
    def generate_contributing(self) -> str:
        lines = ["## Contributing", ""]
        lines.append("Contributions are welcome! Please feel free to submit a Pull Request.")
        lines.append("")
        return "\n".join(lines)
    
    def generate_license(self) -> str:
        lines = ["## License", ""]
        license_name = self.metadata.get("license", "MIT")
        lines.append(f"This project is licensed under the {license_name} License.")
        lines.append("")
        return "\n".join(lines)
    
    def generate_custom(self, title: str, content: str = "") -> str:
        lines = [f"## {title}", ""]
        if content:
            lines.append(content)
        else:
            lines.append("<!-- Add your content here -->")
        lines.append("")
        return "\n".join(lines)


class TemplateEngine:
    """Template engine for README generation."""
    
    def __init__(self, metadata: Dict[str, Any], dependencies: Dict[str, List[str]]):
        self.metadata = metadata
        self.dependencies = dependencies
        self.section_gen = SectionGenerator(metadata, dependencies)
    
    def render_template(self, template_path: Optional[Path] = None) -> str:
        if template_path and template_path.exists():
            return self._render_custom_template(template_path)
        return self._render_default_template()
    
    def _render_custom_template(self, template_path: Path) -> str:
        content = template_path.read_text(encoding="utf-8", errors="ignore")
        
        replacements = {
            "{{name}}": self.metadata.get("name", ""),
            "{{version}}": self.metadata.get("version", ""),
            "{{description}}": self.metadata.get("description", ""),
            "{{author}}": self.metadata.get("author", ""),
            "{{license}}": self.metadata.get("license", ""),
            "{{language}}": self.metadata.get("language", ""),
            "{{year}}": str(datetime.now().year),
        }
        
        for placeholder, value in replacements.items():
            content = content.replace(placeholder, value)
        
        return content
    
    def _render_default_template(self) -> str:
        sections = [
            self.section_gen.generate_title(),
            self.section_gen.generate_description(),
            self.section_gen.generate_installation(),
            self.section_gen.generate_usage(),
            self.section_gen.generate_contributing(),
            self.section_gen.generate_license(),
        ]
        
        return "\n".join(sections)


class ReadmeGenerator:
    """Main README generator class."""
    
    def __init__(self, root: Path, config: Optional[Dict[str, Any]] = None):
        self.root = root
        self.config = config or {}
        
        self.metadata = MetadataExtractor(root).extract_all()
        self.dependencies = DependencyAnalyzer(root).get_dependencies()
        self.template_engine = TemplateEngine(self.metadata, self.dependencies)
    
    def generate(
        self,
        sections: Optional[List[str]] = None,
        template_path: Optional[Path] = None,
        badge_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate README content."""
        
        if template_path:
            return self.template_engine.render_template(template_path)
        
        section_gen = self.template_engine.section_gen
        section_map = {
            "title": section_gen.generate_title,
            "description": section_gen.generate_description,
            "badges": lambda: section_gen.generate_badges(badge_config),
            "installation": section_gen.generate_installation,
            "usage": section_gen.generate_usage,
            "dependencies": section_gen.generate_dependencies,
            "contributing": section_gen.generate_contributing,
            "license": section_gen.generate_license,
        }
        
        if sections:
            content = []
            for section in sections:
                if section in section_map:
                    content.append(section_map[section]())
                else:
                    content.append(section_gen.generate_custom(section))
            return "\n".join(content)
        
        return self.template_engine.render_template()
    
    def save(self, content: str, output_path: Path) -> None:
        """Save README to file."""
        output_path.write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Universal README Generator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--path", default=".", help="Project root directory")
    parser.add_argument("--output", default="README.md", help="Output file name")
    parser.add_argument("--config", help="Configuration file (JSON/YAML/TOML)")
    parser.add_argument("--template", help="Custom template file")
    parser.add_argument("--sections", nargs="*", help="Sections to include (default: all)")
    parser.add_argument("--no-badges", action="store_true", help="Exclude badges")
    parser.add_argument("--dry-run", action="store_true", help="Print to stdout instead of writing file")
    parser.add_argument("--output-format", choices=["md", "rst", "txt"], default="md", help="Output format")

    args = parser.parse_args()

    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"Error: '{args.path}' is not a directory", file=sys.stderr)
        sys.exit(1)

    config = None
    if args.config:
        config_path = Path(args.config)
        config = ConfigLoader.load_any(config_path)

    badge_config = None
    if not args.no_badges:
        badge_config = config.get("badges", {}) if config else None

    generator = ReadmeGenerator(root, config)
    
    template_path = Path(args.template) if args.template else None
    content = generator.generate(
        sections=args.sections,
        template_path=template_path,
        badge_config=badge_config,
    )

    if args.dry_run:
        print(content)
    else:
        output_path = root / args.output
        generator.save(content, output_path)
        print(f"README generated: {output_path}")


if __name__ == "__main__":
    main()
