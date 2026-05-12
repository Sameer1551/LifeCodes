#!/usr/bin/env python3
"""
Image Metadata Reader Tool
Extract EXIF metadata from image files.
"""

import argparse
import json
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

try:
    import exifread
    HAS_EXIFREAD = True
except ImportError:
    HAS_EXIFREAD = False


SUPPORTED_FORMATS = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tiff', '.tif')


def _get_exif_data_pil(image_path: str) -> dict:
    """Extract EXIF data using Pillow."""
    img = Image.open(image_path)
    exif_data = {}

    if hasattr(img, '_getexif') and img._getexif():
        raw_exif = img._getexif()
        for tag_id, value in raw_exif.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == 'GPSInfo':
                gps_data = {}
                for gps_id in value:
                    gps_tag = GPSTAGS.get(gps_id, gps_id)
                    gps_data[gps_tag] = value[gps_id]
                exif_data[tag] = gps_data
            else:
                exif_data[tag] = value

    return exif_data


def _get_exif_data_exifread(image_path: str) -> dict:
    """Extract comprehensive EXIF data using exifread."""
    if not HAS_EXIFREAD:
        return {}

    with open(image_path, 'rb') as f:
        tags = exifread.process_file(f)

    exif_data = {}
    for tag, value in tags.items():
        # Skip thumbnail data
        if 'Thumbnail' in tag:
            continue
        exif_data[tag] = str(value)

    return exif_data


def _convert_to_serializable(obj):
    """Convert non-serializable objects to strings for JSON output."""
    if isinstance(obj, bytes):
        return obj.decode('utf-8', errors='replace')
    elif isinstance(obj, tuple):
        return list(_convert_to_serializable(v) for v in obj)
    elif isinstance(obj, dict):
        return {k: _convert_to_serializable(v) for k, v in obj.items()}
    return obj


def read_metadata(
    image_path: str,
    include_gps: bool = True,
    use_exifread: bool = True
) -> dict:
    """
    Extract EXIF metadata from an image file.

    Args:
        image_path: Path to image file.
        include_gps: Include GPS data in output.
        use_exifread: Use exifread library for comprehensive data.

    Returns:
        Dictionary containing EXIF metadata.
    """
    img = Image.open(image_path)
    metadata = {
        'file': {
            'filename': Path(image_path).name,
            'format': img.format,
            'mode': img.mode,
            'size': img.size,
            'width': img.width,
            'height': img.height
        }
    }

    # Use exifread for comprehensive data if available
    if use_exifread and HAS_EXIFREAD:
        exif_data = _get_exif_data_exifread(image_path)
        if exif_data:
            metadata['exif'] = exif_data
    else:
        # Fall back to Pillow's limited EXIF extraction
        exif_data = _get_exif_data_pil(image_path)
        if exif_data:
            metadata['exif'] = exif_data

    # Filter GPS data if requested
    if not include_gps and 'exif' in metadata:
        metadata['exif'] = {
            k: v for k, v in metadata['exif'].items()
            if 'GPS' not in str(k).upper()
        }

    return metadata


def read_metadata_directory(
    directory: str,
    include_gps: bool = True,
    use_exifread: bool = True,
    verbose: bool = False
) -> list[dict]:
    """
    Extract metadata from all images in a directory.

    Args:
        directory: Path to directory.
        include_gps: Include GPS data.
        use_exifread: Use exifread library.
        verbose: Print progress information.

    Returns:
        List of metadata dictionaries.
    """
    dir_path = Path(directory)
    image_files = [f for f in dir_path.iterdir() if f.suffix.lower() in SUPPORTED_FORMATS]

    results = []
    for img_file in image_files:
        if verbose:
            print(f"Reading: {img_file.name}")

        try:
            metadata = read_metadata(
                str(img_file),
                include_gps=include_gps,
                use_exifread=use_exifread
            )
            results.append(metadata)
        except Exception as e:
            print(f"Error reading {img_file.name}: {e}")

    return results


def format_metadata_human(metadata: dict) -> str:
    """Format metadata as human-readable text."""
    lines = []
    lines.append(f"File: {metadata['file']['filename']}")
    lines.append(f"  Format: {metadata['file']['format']}")
    lines.append(f"  Mode: {metadata['file']['mode']}")
    lines.append(f"  Dimensions: {metadata['file']['width']} x {metadata['file']['height']}")

    if 'exif' in metadata:
        lines.append("  EXIF Data:")
        for key, value in metadata['exif'].items():
            # Truncate long values
            value_str = str(value)
            if len(value_str) > 100:
                value_str = value_str[:97] + '...'
            lines.append(f"    {key}: {value_str}")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Extract EXIF metadata from images."
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
        "--json",
        action="store_true",
        help="Output in JSON format"
    )
    parser.add_argument(
        "--no-gps",
        action="store_true",
        help="Exclude GPS data from output"
    )
    parser.add_argument(
        "--no-exifread",
        action="store_true",
        help="Do not use exifread library (Pillow only)"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Output file path (optional)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print progress information"
    )

    args = parser.parse_args()

    if not args.input and not args.directory:
        parser.error("Either --input or --directory is required")

    use_exifread = not args.no_exifread
    if use_exifread and not HAS_EXIFREAD:
        print("Warning: exifread not installed, using Pillow only")
        use_exifread = False

    if args.directory:
        results = read_metadata_directory(
            args.directory,
            include_gps=not args.no_gps,
            use_exifread=use_exifread,
            verbose=args.verbose
        )

        if args.json:
            output = json.dumps(results, indent=2, default=_convert_to_serializable)
        else:
            output = '\n\n'.join(format_metadata_human(m) for m in results)

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"Metadata written to {args.output}")
        else:
            print(output)

        print(f"\nProcessed {len(results)} images")
    else:
        metadata = read_metadata(
            args.input,
            include_gps=not args.no_gps,
            use_exifread=use_exifread
        )

        if args.json:
            output = json.dumps(metadata, indent=2, default=_convert_to_serializable)
        else:
            output = format_metadata_human(metadata)

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"Metadata written to {args.output}")
        else:
            print(output)


if __name__ == "__main__":
    main()