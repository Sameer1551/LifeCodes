#!/usr/bin/env python3
"""
Image Compressor Tool
Reduce image file size while maintaining acceptable quality.
"""

import argparse
import os
from pathlib import Path
from PIL import Image


SUPPORTED_FORMATS = ('.png', '.jpg', '.jpeg', '.webp', '.tiff')


def get_file_size(path: str) -> int:
    """Get file size in bytes."""
    return os.path.getsize(path)


def compress_image(
    input_path: str,
    output_path: str,
    quality: int = 85,
    max_width: int | None = None,
    max_height: int | None = None,
    target_size: int | None = None,
    optimize: bool = True,
    verbose: bool = False
) -> tuple[str, int, int]:
    """
    Compress an image to reduce file size.

    Args:
        input_path: Path to input image.
        output_path: Path to save compressed image.
        quality: Quality for lossy formats (1-100).
        max_width: Maximum width (will resize if exceeded).
        max_height: Maximum height (will resize if exceeded).
        target_size: Target file size in bytes (iterative compression).
        optimize: Enable PNG optimization.
        verbose: Print compression details.

    Returns:
        Tuple of (output_path, original_size, compressed_size).
    """
    img = Image.open(input_path)
    original_size = get_file_size(input_path)

    # Resize if max dimensions specified
    if max_width or max_height:
        orig_width, orig_height = img.size
        new_width, new_height = orig_width, orig_height

        if max_width and orig_width > max_width:
            ratio = max_width / orig_width
            new_width = max_width
            new_height = int(orig_height * ratio)

        if max_height and new_height > max_height:
            ratio = max_height / new_height
            new_height = max_height
            new_width = int(new_width * ratio)

        if new_width != orig_width or new_height != orig_height:
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            if verbose:
                print(f"Resized from {orig_width}x{orig_height} to {new_width}x{new_height}")

    # Determine output format
    output_ext = Path(output_path).suffix.lower()

    # Handle format conversions
    if output_ext in ('.jpg', '.jpeg'):
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

    # Initial save
    save_kwargs = {}
    if output_ext in ('.jpg', '.jpeg', '.webp'):
        save_kwargs['quality'] = quality
    elif output_ext == '.png':
        save_kwargs['optimize'] = optimize

    img.save(output_path, **save_kwargs)

    # Iterative compression for target size
    if target_size and output_ext in ('.jpg', '.jpeg', '.webp'):
        current_quality = quality
        current_size = get_file_size(output_path)

        while current_size > target_size and current_quality > 10:
            current_quality -= 5
            img.save(output_path, quality=current_quality)
            current_size = get_file_size(output_path)

            if verbose:
                print(f"Quality: {current_quality}, Size: {current_size} bytes")

    compressed_size = get_file_size(output_path)
    return output_path, original_size, compressed_size


def compress_directory(
    input_dir: str,
    output_dir: str,
    quality: int = 85,
    max_width: int | None = None,
    max_height: int | None = None,
    target_size: int | None = None,
    optimize: bool = True,
    verbose: bool = False
) -> list[tuple[str, int, int]]:
    """
    Compress all images in a directory.

    Args:
        input_dir: Path to input directory.
        output_dir: Path to output directory.
        quality: Quality for lossy formats.
        max_width: Maximum width.
        max_height: Maximum height.
        target_size: Target file size in bytes.
        optimize: Enable PNG optimization.
        verbose: Print progress information.

    Returns:
        List of tuples (path, original_size, compressed_size).
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    results = []
    image_files = [f for f in input_path.iterdir() if f.suffix.lower() in SUPPORTED_FORMATS]

    for img_file in image_files:
        out_file = output_path / img_file.name

        if verbose:
            print(f"Compressing: {img_file.name}")

        try:
            result = compress_image(
                str(img_file),
                str(out_file),
                quality=quality,
                max_width=max_width,
                max_height=max_height,
                target_size=target_size,
                optimize=optimize,
                verbose=verbose
            )
            results.append(result)
        except Exception as e:
            print(f"Error compressing {img_file.name}: {e}")

    return results


def format_size(size_bytes: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"


def main():
    parser = argparse.ArgumentParser(
        description="Compress images to reduce file size."
    )
    parser.add_argument(
        "-i", "--input",
        type=str,
        help="Input image file"
    )
    parser.add_argument(
        "-d", "--directory",
        type=str,
        help="Input directory (batch mode)"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        required=True,
        help="Output file or directory"
    )
    parser.add_argument(
        "-q", "--quality",
        type=int,
        default=85,
        help="Quality for lossy formats 1-100 (default: 85)"
    )
    parser.add_argument(
        "--max-width",
        type=int,
        help="Maximum width in pixels"
    )
    parser.add_argument(
        "--max-height",
        type=int,
        help="Maximum height in pixels"
    )
    parser.add_argument(
        "--target-size",
        type=int,
        help="Target file size in bytes (iterative compression)"
    )
    parser.add_argument(
        "--no-optimize",
        action="store_true",
        help="Disable PNG optimization"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print compression details"
    )

    args = parser.parse_args()

    if not args.input and not args.directory:
        parser.error("Either --input or --directory is required")

    if args.directory:
        results = compress_directory(
            args.directory,
            args.output,
            quality=args.quality,
            max_width=args.max_width,
            max_height=args.max_height,
            target_size=args.target_size,
            optimize=not args.no_optimize,
            verbose=args.verbose
        )

        print(f"\nCompressed {len(results)} images:")
        total_original = 0
        total_compressed = 0
        for path, orig_size, comp_size in results:
            reduction = (1 - comp_size / orig_size) * 100 if orig_size > 0 else 0
            total_original += orig_size
            total_compressed += comp_size
            print(f"  {Path(path).name}: {format_size(orig_size)} -> {format_size(comp_size)} ({reduction:.1f}% reduction)")

        total_reduction = (1 - total_compressed / total_original) * 100 if total_original > 0 else 0
        print(f"\nTotal: {format_size(total_original)} -> {format_size(total_compressed)} ({total_reduction:.1f}% reduction)")
    else:
        _, orig_size, comp_size = compress_image(
            args.input,
            args.output,
            quality=args.quality,
            max_width=args.max_width,
            max_height=args.max_height,
            target_size=args.target_size,
            optimize=not args.no_optimize,
            verbose=args.verbose
        )

        reduction = (1 - comp_size / orig_size) * 100 if orig_size > 0 else 0
        print(f"Compressed: {format_size(orig_size)} -> {format_size(comp_size)} ({reduction:.1f}% reduction)")
        print(f"Saved to: {args.output}")


if __name__ == "__main__":
    main()