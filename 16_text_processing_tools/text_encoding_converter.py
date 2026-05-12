#!/usr/bin/env python3
"""
Text Encoding Converter Tool
Detect and convert text encoding to UTF-8.
"""

import argparse
import chardet
from pathlib import Path
from typing import Optional


def detect_encoding(file_path: str) -> dict:
    """
    Detect the encoding of a file.

    Args:
        file_path: Path to the file.

    Returns:
        Dict with encoding, confidence, and language.
    """
    with open(file_path, "rb") as f:
        raw_data = f.read()

    result = chardet.detect(raw_data)
    return {
        "encoding": result["encoding"],
        "confidence": result["confidence"],
        "language": result.get("language", "unknown")
    }


def convert_encoding(
    input_path: str,
    output_path: Optional[str] = None,
    target_encoding: str = "utf-8",
    fallback_encodings: Optional[list[str]] = None
) -> tuple[str, str]:
    """
    Convert file to target encoding.

    Args:
        input_path: Path to input file.
        output_path: Path to output file (optional, defaults to input_path).
        target_encoding: Target encoding (default: utf-8).
        fallback_encodings: List of encodings to try if detection fails.

    Returns:
        Tuple of (detected_encoding, output_path).
    """
    if fallback_encodings is None:
        fallback_encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]

    with open(input_path, "rb") as f:
        raw_data = f.read()

    detected = chardet.detect(raw_data)
    encoding = detected["encoding"]

    text = None
    tried_encodings = []

    if encoding:
        try:
            text = raw_data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            tried_encodings.append(encoding)

    if text is None:
        for enc in fallback_encodings:
            if enc not in tried_encodings:
                try:
                    text = raw_data.decode(enc)
                    encoding = enc
                    break
                except (UnicodeDecodeError, LookupError):
                    tried_encodings.append(enc)

    if text is None:
        raise ValueError(
            f"Could not decode file with any encoding. "
            f"Tried: {encoding}, {', '.join(fallback_encodings)}"
        )

    if output_path is None:
        output_path = input_path

    with open(output_path, "w", encoding=target_encoding) as f:
        f.write(text)

    return encoding, output_path


def batch_convert(
    input_dir: str,
    output_dir: Optional[str] = None,
    pattern: str = "*",
    target_encoding: str = "utf-8"
) -> list[dict]:
    """
    Convert all matching files in a directory.

    Args:
        input_dir: Input directory path.
        output_dir: Output directory path (optional).
        pattern: File pattern to match.
        target_encoding: Target encoding.

    Returns:
        List of conversion results.
    """
    input_path = Path(input_dir)
    files = list(input_path.glob(pattern))

    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
    else:
        output_path = input_path

    results = []
    for file in files:
        try:
            detected_encoding, out_file = convert_encoding(
                str(file),
                str(output_path / file.name) if output_dir else None,
                target_encoding
            )
            results.append({
                "file": str(file),
                "detected_encoding": detected_encoding,
                "output": str(out_file) if output_dir else str(file),
                "status": "success"
            })
        except Exception as e:
            results.append({
                "file": str(file),
                "error": str(e),
                "status": "failed"
            })

    return results


def show_encoding_info(file_path: str) -> None:
    """Display encoding information for a file."""
    info = detect_encoding(file_path)

    print(f"\nFile: {file_path}")
    print("-" * 50)
    print(f"Detected encoding: {info['encoding']}")
    print(f"Confidence: {info['confidence']*100:.1f}%")
    print(f"Language: {info['language']}")

    with open(file_path, "rb") as f:
        raw_data = f.read()
    print(f"File size: {len(raw_data)} bytes")

    try:
        text = raw_data.decode(info['encoding'])
        print(f"Character count: {len(text)}")
        print(f"\nPreview (first 200 chars):\n{text[:200]}...")
    except (UnicodeDecodeError, LookupError):
        print("Could not decode file for preview")


def main():
    parser = argparse.ArgumentParser(
        description="Detect and convert text encoding."
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Detect command
    detect_parser = subparsers.add_parser("detect", help="Detect file encoding")
    detect_parser.add_argument(
        "file",
        type=str,
        help="File to analyze"
    )

    # Convert command
    convert_parser = subparsers.add_parser("convert", help="Convert file encoding")
    convert_parser.add_argument(
        "input",
        type=str,
        help="Input file path"
    )
    convert_parser.add_argument(
        "-o", "--output",
        type=str,
        help="Output file path (default: overwrite input)"
    )
    convert_parser.add_argument(
        "-e", "--encoding",
        type=str,
        default="utf-8",
        help="Target encoding (default: utf-8)"
    )
    convert_parser.add_argument(
        "--fallback",
        type=str,
        nargs="+",
        help="Fallback encodings to try"
    )

    # Batch command
    batch_parser = subparsers.add_parser("batch", help="Batch convert files")
    batch_parser.add_argument(
        "directory",
        type=str,
        help="Input directory"
    )
    batch_parser.add_argument(
        "-o", "--output",
        type=str,
        help="Output directory"
    )
    batch_parser.add_argument(
        "-p", "--pattern",
        type=str,
        default="*",
        help="File glob pattern to match (default: * = all files). Example: '*.txt', '*.csv', '*.log'"
    )
    batch_parser.add_argument(
        "-e", "--encoding",
        type=str,
        default="utf-8",
        help="Target encoding (default: utf-8)"
    )

    args = parser.parse_args()

    if args.command == "detect":
        show_encoding_info(args.file)

    elif args.command == "convert":
        original_encoding, output_path = convert_encoding(
            args.input,
            args.output,
            args.encoding,
            args.fallback
        )
        print(f"Converted from {original_encoding} to {args.encoding}")
        print(f"Output saved to: {output_path}")

    elif args.command == "batch":
        results = batch_convert(
            args.directory,
            args.output,
            args.pattern,
            args.encoding
        )

        print(f"\nBatch conversion results ({len(results)} files):")
        print("-" * 60)

        success_count = 0
        for result in results:
            if result["status"] == "success":
                print(f"✓ {result['file']}")
                print(f"  {result['detected_encoding']} → {args.encoding}")
                success_count += 1
            else:
                print(f"✗ {result['file']}")
                print(f"  Error: {result['error']}")

        print(f"\nConverted {success_count}/{len(results)} files successfully")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()