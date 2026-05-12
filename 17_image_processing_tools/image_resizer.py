#!/usr/bin/env python3
"""
Image Resizer Tool
Resize single or multiple images to specific dimensions or by percentage.
"""

import argparse
import os
from pathlib import Path
from PIL import Image


SUPPORTED_FORMATS = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tiff')


def resize_image(
    input_path: str,
    output_path: str,
    width: int | None = None,
    height: int | None = None,
    scale: float | None = None,
    keep_aspect: bool = True,
    output_format: str | None = None
) -> str:
    """
    Resize an image to specified dimensions or by percentage.

    Args:
        input_path: Path to input image file.
        output_path: Path to save resized image.
        width: Target width in pixels.
        height: Target height in pixels.
        scale: Scale factor (e.g., 0.5 for 50%, 2.0 for 200%).
        keep_aspect: Maintain aspect ratio when resizing.
        output_format: Output format (png/jpg/webp/bmp/gif/tiff).

    Returns:
        Path to the resized image.
    """
    img = Image.open(input_path)
    original_width, original_height = img.size

    if scale is not None:
        new_width = int(original_width * scale)
        new_height = int(original_height * scale)
    elif width is not None and height is not None:
        if keep_aspect:
            # Calculate aspect-preserving dimensions
            aspect_ratio = original_width / original_height
            if width / height > aspect_ratio:
                new_width = int(height * aspect_ratio)
                new_height = height
            else:
                new_width = width
                new_height = int(width / aspect_ratio)
        else:
            new_width = width
            new_height = height
    elif width is not None:
        if keep_aspect:
            new_width = width
            new_height = int(original_height * (width / original_width))
        else:
            new_width = width
            new_height = original_height
    elif height is not None:
        if keep_aspect:
            new_height = height
            new_width = int(original_width * (height / original_height))
        else:
            new_width = original_width
            new_height = height
    else:
        raise ValueError("Either width, height, or scale must be specified")

    # Use LANCZOS for high-quality downsampling
    resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Determine output format
    if output_format:
        format_upper = output_format.upper()
        if format_upper == 'JPG':
            format_upper = 'JPEG'
    else:
        output_format = Path(output_path).suffix.lstrip('.').lower()
        if output_format == 'jpg':
            output_format = 'jpeg'

    # Handle format-specific options
    save_kwargs = {}
    if output_format in ('jpeg', 'jpg') and img.mode in ('RGBA', 'P'):
        resized = resized.convert('RGB')

    resized.save(output_path, **save_kwargs)
    return output_path


def resize_directory(
    input_dir: str,
    output_dir: str,
    width: int | None = None,
    height: int | None = None,
    scale: float | None = None,
    keep_aspect: bool = True,
    output_format: str | None = None,
    verbose: bool = False
) -> list[str]:
    """
    Resize all images in a directory.

    Args:
        input_dir: Path to input directory.
        output_dir: Path to output directory.
        width: Target width in pixels.
        height: Target height in pixels.
        scale: Scale factor.
        keep_aspect: Maintain aspect ratio.
        output_format: Output format for all images.
        verbose: Print progress information.

    Returns:
        List of paths to resized images.
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    resized_files = []
    image_files = [f for f in input_path.iterdir() if f.suffix.lower() in SUPPORTED_FORMATS]

    for img_file in image_files:
        if output_format:
            suffix = f'.{output_format.lower()}'
            if suffix == '.jpg':
                suffix = '.jpeg' if img_file.suffix.lower() == '.jpeg' else '.jpg'
        else:
            suffix = img_file.suffix

        out_file = output_path / f"{img_file.stem}{suffix}"

        if verbose:
            print(f"Resizing: {img_file.name} -> {out_file.name}")

        try:
            resize_image(
                str(img_file),
                str(out_file),
                width=width,
                height=height,
                scale=scale,
                keep_aspect=keep_aspect,
                output_format=output_format
            )
            resized_files.append(str(out_file))
        except Exception as e:
            print(f"Error resizing {img_file.name}: {e}")

    return resized_files


def main():
    parser = argparse.ArgumentParser(
        description="Resize images by dimensions or percentage."
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
        "--width",
        type=int,
        help="Target width in pixels"
    )
    parser.add_argument(
        "--height",
        type=int,
        help="Target height in pixels"
    )
    parser.add_argument(
        "--scale",
        type=float,
        help="Scale factor (e.g., 0.5 for 50%%, 2.0 for 200%%)"
    )
    parser.add_argument(
        "--no-aspect",
        action="store_true",
        help="Disable aspect ratio preservation"
    )
    parser.add_argument(
        "-f", "--format",
        type=str,
        choices=['png', 'jpg', 'jpeg', 'webp', 'bmp', 'gif', 'tiff'],
        help="Output format"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print progress information"
    )

    args = parser.parse_args()

    if not args.input and not args.directory:
        parser.error("Either --input or --directory is required")

    if args.width is None and args.height is None and args.scale is None:
        parser.error("At least one of --width, --height, or --scale is required")

    if args.directory:
        files = resize_directory(
            args.directory,
            args.output,
            width=args.width,
            height=args.height,
            scale=args.scale,
            keep_aspect=not args.no_aspect,
            output_format=args.format,
            verbose=args.verbose
        )
        print(f"Resized {len(files)} images to {args.output}")
    else:
        resize_image(
            args.input,
            args.output,
            width=args.width,
            height=args.height,
            scale=args.scale,
            keep_aspect=not args.no_aspect,
            output_format=args.format
        )
        print(f"Resized image saved to {args.output}")


if __name__ == "__main__":
    main()