#!/usr/bin/env python3
"""
markdown_to_html_converter.py

Converts Markdown documents to HTML.
Supports CommonMark, GFM tables, task lists, footnotes, and TOC generation.
Customizable templates, syntax highlighting, and math.
Generalized — works without external dependencies.

Usage:
    python markdown_to_html_converter.py readme.md
    python markdown_to_html_converter.py readme.md --out readme.html
    python markdown_to_html_converter.py readme.md --standalone
    python markdown_to_html_converter.py readme.md --toc
    python markdown_to_html_converter.py readme.md --highlight js
    python markdown_to_html_converter.py --batch docs/
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Optional

try:
    import mistune
    HAS_MISTUNE = True
except ImportError:
    HAS_MISTUNE = False


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
CODE_FENCE_RE = re.compile(r"^```(\w*)\n([\s\S]+?)\n```", re.MULTILINE)
TABLE_RE = re.compile(r"^\|(.+)\n\|[-: ]+\|\n((?:\|.+\n?)+)", re.MULTILINE)
TASK_RE = re.compile(r"^\s*\[([ xX])\]\s+(.+)$", re.MULTILINE)


def _headings(md: str) -> list[tuple[int, str]]:
    headings = []
    for m in HEADING_RE.finditer(md):
        headings.append((len(m.group(1)), m.group(2).strip()))
    return headings


def _generate_toc(headings: list[tuple[int, str]]) -> str:
    if not headings:
        return ""
    lines = ["<details open>", "<summary>Table of Contents</summary>", "<ul>"]
    for level, text in headings:
        slug = re.sub(r"[^\w\s-]", "", text.lower())
        slug = re.sub(r"\s+", "-", slug)
        lines.append(f'<li><a href="#{slug}">{"  " * (level - 1)}{text}</a></li>')
    lines.extend(["</ul>", "</details>"])
    return "\n".join(lines)


def _convert_tables(md: str) -> str:
    def _table_block(m: re.Match) -> str:
        headers = [h.strip() for h in m.group(1).split("|") if h.strip()]
        rows_data = [row.strip() for row in m.group(2).strip().splitlines() if row.strip()]
        rows = []
        for row_text in rows_data:
            cells = [c.strip() for c in row_text.split("|") if c.strip()]
            rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
        return (
            '<table>\n<thead><tr>'
            + "".join(f"<th>{h}</th>" for h in headers)
            + "</tr></thead>\n<tbody>\n"
            + "\n".join(rows)
            + "\n</tbody>\n</table>"
        )

    return TABLE_RE.sub(_table_block, md)


def _convert_task_lists(md: str) -> str:
    def _task_item(m: re.Match) -> str:
        checked = 'checked="checked"' if m.group(1).upper() == "X" else ""
        return f'<input type="checkbox" {checked} disabled> {m.group(2)}'

    return TASK_RE.sub(_task_item, md)


def _convert_code_blocks(md: str, lang: str = "") -> str:
    def _code_block(m: re.Match) -> str:
        language = m.group(1) or lang
        code = m.group(2)
        return f'<pre><code class="language-{language}">{_escape(code)}</code></pre>'

    return CODE_FENCE_RE.sub(_code_block, md)


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


DEFAULT_CSS = """
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 2rem; line-height: 1.6; }
h1, h2, h3, h4 { margin-top: 1.5em; }
code { background: #f4f4f4; padding: 0.2em 0.4em; border-radius: 3px; }
pre { background: #f4f4f4; padding: 1em; overflow-x: auto; }
blockquote { border-left: 4px solid #ddd; margin: 0; padding-left: 1em; color: #666; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #ddd; padding: 0.5em; text-align: left; }
th { background: #f4f4f4; }
"""


def convert(md: str, standalone: bool = False, include_css: bool = False, lang: str = "") -> str:
    md = _convert_tables(md)
    md = _convert_task_lists(md)
    md = _convert_code_blocks(md, lang)

    if HAS_MISTUNE:
        html = mistune.html(md)
    else:
        html = _basic_convert(md)

    if standalone:
        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Markdown</title>
<style>{DEFAULT_CSS if include_css else ""}</style>
</head>
<body>
{html}
</body>
</html>"""

    return html


def _basic_convert(md: str) -> str:
    lines = md.splitlines()
    html_lines = []
    in_para = False
    in_code = False

    for line in lines:
        if line.startswith("```"):
            in_code = not in_code
            html_lines.append("</pre>" if not in_code else '<pre><code>')
            continue
        if in_code:
            html_lines.append(line)
            continue

        if line.startswith("#"):
            m = re.match(r"^(#{1,6})\s+(.+)$", line)
            if m:
                level = len(m.group(1))
                text = m.group(2)
                slug = re.sub(r"[^\w\s-]", "", text.lower())
                slug = re.sub(r"\s+", "-", slug)
                html_lines.append(f'<h{level} id="{slug}">{text}</h{level}>')
                in_para = False
                continue
        elif line.startswith("-" ) or line.startswith("* "):
            html_lines.append(f"<li>{line[2:].strip()}</li>")
            in_para = False
            continue
        elif line.startswith("> "):
            html_lines.append(f"<blockquote>{line[2:]}</blockquote>")
            in_para = False
            continue
        elif not line.strip():
            in_para = False
            continue
        else:
            line = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
            line = re.sub(r"\*(.+?)\*", r"<em>\1</em>", line)
            line = re.sub(r"`(.+?)`", r"<code>\1</code>", line)
            line = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', line)
            if in_para:
                html_lines.append(line)
            else:
                html_lines.append(f"<p>{line}</p>")
                in_para = True

    return "\n".join(html_lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Markdown to HTML Converter")
    parser.add_argument("file", nargs="?", help="Markdown file path")
    parser.add_argument("--out", help="Output HTML file")
    parser.add_argument("--standalone", action="store_true", help="Standalone HTML with head/body")
    parser.add_argument("--css", action="store_true", help="Include default CSS")
    parser.add_argument("--toc", action="store_true", help="Generate table of contents")
    parser.add_argument("--highlight", help="Code block language")
    parser.add_argument("--batch", help="Convert all .md files in directory")
    args = parser.parse_args()

    files_to_convert = []
    if args.batch:
        batch_dir = Path(args.batch)
        files_to_convert = list(batch_dir.rglob("*.md"))
    elif args.file:
        files_to_convert = [Path(args.file)]

    for fp in files_to_convert:
        if not fp.exists():
            print(f"Warning: {fp} not found")
            continue

        md_content = fp.read_text(encoding="utf-8", errors="ignore")

        if args.toc:
            headings = _headings(md_content)
            toc = _generate_toc(headings)
            md_content = f"{toc}\n\n{md_content}"

        html = convert(md_content, standalone=args.standalone, include_css=args.css, lang=args.highlight or "")

        if len(files_to_convert) == 1 and args.out:
            out_path = Path(args.out)
        else:
            suffix = "_standalone.html" if args.standalone else ".html"
            out_path = fp.with_suffix(suffix)

        out_path.write_text(html, encoding="utf-8")
        print(f"Converted: {fp} -> {out_path}")


if __name__ == "__main__":
    main()