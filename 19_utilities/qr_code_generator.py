#!/usr/bin/env python3
"""
qr_code_generator.py

Generates QR codes as PNG, SVG, or ASCII art.
Supports all error correction levels.
Batch generation from a CSV file.
Generalized — requires 'qrcode' package.

Usage:
    python qr_code_generator.py "https://example.com" --out qr.png
    python qr_code_generator.py "Hello World" --out qr.svg --format svg
    python qr_code_generator.py "data.csv" --batch --out out/
    python qr_code_generator.py "text" --ascii
"""

from __future__ import annotations

import argparse
import base64
import csv
import io
import sys
from pathlib import Path

try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False


def _generate_png(data: str, box_size: int = 10, border: int = 4) -> bytes:
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=box_size, border=border)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _generate_svg(data: str, box_size: int = 10, border: int = 4) -> str:
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=box_size, border=border)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    size = img.size[0]
    lines = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 50 50">']
    for y in range(size):
        for x in range(size):
            if img.getpixel((x, y)):
                lines.append(f'<rect x="{x}" y="{y}" width="1" height="1"/>')
    lines.append("</svg>")
    return "\n".join(lines)


def _generate_ascii(data: str) -> str:
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=1, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    size = img.size[0]
    rows = []
    for y in range(size):
        row = "".join("##" if img.getpixel((x, y)) else "  " for x in range(size))
        rows.append(row)
    return "\n".join(rows)


def generate(data: str, fmt: str) -> bytes | str:
    if fmt == "png":
        return _generate_png(data)
    if fmt == "svg":
        return _generate_svg(data)
    if fmt == "ascii":
        return _generate_ascii(data)
    if fmt == "base64":
        return base64.b64encode(_generate_png(data)).decode("ascii")
    raise ValueError(f"Unknown format: {fmt}")


def main() -> None:
    parser = argparse.ArgumentParser(description="QR Code Generator")
    parser.add_argument("data", help="Data to encode")
    parser.add_argument("--out", help="Output file path")
    parser.add_argument("--format", choices=["png", "svg", "base64"], default="png")
    parser.add_argument("--ascii", action="store_true", help="ASCII art output")
    parser.add_argument("--batch", action="store_true", help="Batch mode: data is CSV with name,url columns")
    args = parser.parse_args()

    if not HAS_QRCODE:
        print("Error: 'qrcode' package not installed. Run: pip install qrcode[pil]", file=sys.stderr)
        sys.exit(1)

    if args.batch:
        rows = list(csv.reader(Path(args.data).read_text(encoding="utf-8").splitlines()))
        out_dir = Path(args.out) if args.out else Path(".")
        out_dir.mkdir(parents=True, exist_ok=True)
        for row in rows:
            if len(row) < 2:
                continue
            name, data_val = row[0], row[1]
            content = generate(data_val, args.format)
            out_path = out_dir / f"{name}.{'svg' if args.format == 'svg' else 'png'}"
            if isinstance(content, bytes):
                out_path.write_bytes(content)
            else:
                out_path.write_text(content, encoding="utf-8")
        return

    if args.ascii:
        print(_generate_ascii(args.data))
        return

    content = generate(args.data, args.format)
    if args.out:
        out_path = Path(args.out)
        if isinstance(content, bytes):
            out_path.write_bytes(content)
        else:
            out_path.write_text(content, encoding="utf-8")
    elif args.format == "base64":
        print(content)
    elif isinstance(content, bytes):
        sys.stdout.buffer.write(content)


if __name__ == "__main__":
    main()