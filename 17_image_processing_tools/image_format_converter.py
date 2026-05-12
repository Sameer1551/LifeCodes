#!/usr/bin/env python3
"""
Image Format Converter Tool
Convert images between formats (PNG, JPG, WEBP, BMP, GIF, TIFF).
"""

import argparse
from pathlib import Path
from PIL import Image


SUPPORTED_FORMATS = {
    '.png': 'PNG',
    '.jpg': 'JPEG',
    '.jpeg': 'JPEG',
    '.webp': 'WEBP',
    '.bmp': 'BMP',
    '.gif': 'GIF',
    '.tiff': 'TIFF',
    '.tif': 'TIFF'
}

IMAGE_EXTENSIONS = tuple(SUPPORTED_FORMATS.keys())


def convert_image(
    input_path: str,
    output_path: str,
    output_format: str | None = None,
    quality: int = 85,
    strip_metadata: bool = False
) -> str:
    """
    Convert an image to a different format.

    Args:
        input_path: Path to input image file.
        output_path: Path to save converted image.
        output_format: Output format (png/jpg/webp/bmp/gif/tiff).
        quality: Quality for lossy formats (1-100).
        strip_metadata: Remove EXIF metadata.

    Returns:
        Path to the converted image.
    """
    img = Image.open(input_path)

    # Determine format
    if output_format:
        format_upper = output_format.upper()
        if format_upper == 'JPG':
            format_upper = 'JPEG'
    else:
        output_path_lower = output_path.lower()
        for ext, fmt in SUPPORTED_FORMATS.items():
            if output_path_lower.endswith(ext):
                format_upper = fmt
                break
        else:
            raise ValueError(f"Cannot determine format from output path: {output_path}")

    # Handle format-specific conversions
    if format_upper == 'JPEG':
        if img.mode in ('RGBA', 'P'):
            # Convert to RGB for JPEG (no transparency support)
            img = img.convert('RGB')
    elif format_upper == 'GIF':
        if img.mode == 'RGBA':
            # GIF supports transparency but needs proper handling
            pass

    # Prepare save kwargs
    save_kwargs = {}
    if format_upper in ('JPEG', 'WEBP'):
        save_kwargs['quality'] = quality
    if format_upper == 'PNG':
        save_kwargs['optimize'] = True

    if strip_metadata:
        # Remove EXIF data by not copying it
        if 'exif' in img.info:
            del img.info['exif']
    else:
        # Preserve EXIF if present
        if 'exif' in img.info and format_upper in ('JPEG', 'PNG', 'WEBP'):
            save_kwargs['exif'] = img.info['exif']

    img.save(output_path, format=format_upper, **save_kwargs)
    return output_path


def convert_directory(
    input_dir: str,
    output_dir: str,
    output_format: str,
    quality: int = 85,
    strip_metadata: bool = False,
    verbose: bool = False
) -> list[str]:
    """
    Convert all images in a directory to a specified format.

    Args:
        input_dir: Path to input directory.
        output_dir: Path to output directory.
        output_format: Target format.
        quality: Quality for lossy formats.
        strip_metadata: Remove EXIF metadata.
        verbose: Print progress information.

    Returns:
        List of paths to converted images.
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    converted_files = []
    image_files = [f for f in input_path.iterdir() if f.suffix.lower() in IMAGE_EXTENSIONS]

    # Determine output extension
    ext_map = {
        'PNG': '.png',
        'JPEG': '.jpg',
        'WEBP': '.webp',
        'BMP': '.bmp',
        'GIF': '.gif',
        'TIFF': '.tiff'
    }
    out_ext = ext_map.get(output_format.upper(), f'.{output_format.lower()}')

    for img_file in image_files:
        out_file = output_path / f"{img_file.stem}{out_ext}"

        if verbose:
            print(f"Converting: {img_file.name} -> {out_file.name}")

        try:
            convert_image(
                str(img_file),
                str(out_file),
                output_format=output_format,
                quality=quality,
                strip_metadata=strip_metadata
            )
            converted_files.append(str(out_file))
        except Exception as e:
            print(f"Error converting {img_file.name}: {e}")

    return converted_files


def main():
    parser = argparse.ArgumentParser(
        description="Convert images between formats."
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
        "-f", "--format",
        type=str,
        choices=['png', 'jpg', 'jpeg', 'webp', 'bmp', 'gif', 'tiff'],
        help="Output format (required for batch mode)"
    )
    parser.add_argument(
        "-q", "--quality",
        type=int,
        default=85,
        help="Quality for lossy formats (1-100, default: 85)"
    )
    parser.add_argument(
        "--strip-metadata",
        action="store_true",
        help="Remove EXIF metadata from output"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print progress information"
    )

    args = parser.parse_args()

    if not args.input and not args.directory:
        parser.error("Either --input or --directory is required")

    if args.directory and not args.format:
        parser.error("--format is required for batch mode")

    if args.directory:
        files = convert_directory(
            args.directory,
            args.output,
            output_format=args.format,
            quality=args.quality,
            strip_metadata=args.strip_metadata,
            verbose=args.verbose
        )
        print(f"Converted {len(files)} images to {args.output}")
    else:
        convert_image(
            args.input,
            args.output,
            output_format=args.format,
            quality=args.quality,
            strip_metadata=args.strip_metadata
        )
        print(f"Converted image saved to {args.output}")


if __name__ == "__main__":
    main()