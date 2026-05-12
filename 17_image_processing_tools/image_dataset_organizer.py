#!/usr/bin/env python3
"""
Image Dataset Organizer Tool
Organize images into folders by date, size, dimensions, or custom criteria.
"""

import argparse
import os
import shutil
from datetime import datetime
from pathlib import Path
from PIL import Image


SUPPORTED_FORMATS = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tiff')


def get_image_metadata(image_path: str) -> dict:
    """
    Extract metadata from an image file.

    Args:
        image_path: Path to image file.

    Returns:
        Dictionary with metadata (date, size, dimensions, color).
    """
    img = Image.open(image_path)
    file_stat = os.stat(image_path)

    metadata = {
        'path': image_path,
        'filename': Path(image_path).name,
        'size_bytes': file_stat.st_size,
        'width': img.width,
        'height': img.height,
        'format': img.format,
        'mode': img.mode
    }

    # Try to get EXIF date
    try:
        if hasattr(img, '_getexif') and img._getexif():
            from PIL.ExifTags import TAGS
            exif = img._getexif()
            for tag_id, value in exif.items():
                tag = TAGS.get(tag_id, tag_id)
                if tag == 'DateTimeOriginal':
                    # Parse EXIF date format: "2024:01:15 10:30:00"
                    metadata['date'] = datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                    break
    except Exception:
        pass

    # Fall back to file modification date
    if 'date' not in metadata:
        metadata['date'] = datetime.fromtimestamp(file_stat.st_mtime)

    # Get dominant color
    try:
        img_small = img.copy()
        img_small.thumbnail((100, 100))
        if img_small.mode != 'RGB':
            img_small = img_small.convert('RGB')

        # Calculate average color
        pixels = list(img_small.getdata())
        avg_r = sum(p[0] for p in pixels) // len(pixels)
        avg_g = sum(p[1] for p in pixels) // len(pixels)
        avg_b = sum(p[2] for p in pixels) // len(pixels)

        # Classify into basic colors
        if avg_r > 200 and avg_g > 200 and avg_b > 200:
            metadata['color'] = 'white'
        elif avg_r < 50 and avg_g < 50 and avg_b < 50:
            metadata['color'] = 'black'
        elif avg_r > avg_g + 50 and avg_r > avg_b + 50:
            metadata['color'] = 'red'
        elif avg_g > avg_r + 50 and avg_g > avg_b + 50:
            metadata['color'] = 'green'
        elif avg_b > avg_r + 50 and avg_b > avg_g + 50:
            metadata['color'] = 'blue'
        elif avg_r > 200 and avg_g > 200 and avg_b < 100:
            metadata['color'] = 'yellow'
        elif avg_r > 200 and avg_g < 100 and avg_b < 100:
            metadata['color'] = 'red'
        elif avg_r > 200 and avg_g < 100 and avg_b > 200:
            metadata['color'] = 'magenta'
        elif avg_r < 100 and avg_g > 200 and avg_b > 200:
            metadata['color'] = 'cyan'
        else:
            metadata['color'] = 'other'
    except Exception:
        metadata['color'] = 'unknown'

    return metadata


def organize_by_date(
    metadata_list: list[dict],
    output_dir: str,
    copy_mode: bool = True,
    dry_run: bool = False
) -> dict[str, list[str]]:
    """Organize images by year/month."""
    output_path = Path(output_dir)
    organized = {}

    for meta in metadata_list:
        date = meta['date']
        year_dir = output_path / str(date.year)
        month_dir = year_dir / f"{date.month:02d}"

        if not dry_run:
            month_dir.mkdir(parents=True, exist_ok=True)

        dest = month_dir / meta['filename']

        if dry_run:
            dest_str = str(dest)
        else:
            if copy_mode:
                shutil.copy2(meta['path'], dest)
            else:
                shutil.move(meta['path'], dest)
            dest_str = str(dest)

        if dest_str not in organized:
            organized[dest_str] = []
        organized[dest_str].append(meta['path'])

    return organized


def organize_by_size(
    metadata_list: list[dict],
    output_dir: str,
    copy_mode: bool = True,
    dry_run: bool = False
) -> dict[str, list[str]]:
    """Organize images by file size ranges."""
    output_path = Path(output_dir)
    organized = {}

    # Size ranges in bytes
    size_ranges = [
        (0, 100 * 1024, 'small'),          # < 100KB
        (100 * 1024, 1024 * 1024, 'medium'),  # 100KB - 1MB
        (1024 * 1024, 10 * 1024 * 1024, 'large'),  # 1MB - 10MB
        (10 * 1024 * 1024, float('inf'), 'very_large')  # > 10MB
    ]

    for meta in metadata_list:
        size = meta['size_bytes']

        # Find appropriate category
        category = 'medium'
        for low, high, cat in size_ranges:
            if low <= size < high:
                category = cat
                break

        size_dir = output_path / category

        if not dry_run:
            size_dir.mkdir(parents=True, exist_ok=True)

        dest = size_dir / meta['filename']

        if dry_run:
            dest_str = str(dest)
        else:
            if copy_mode:
                shutil.copy2(meta['path'], dest)
            else:
                shutil.move(meta['path'], dest)
            dest_str = str(dest)

        if dest_str not in organized:
            organized[dest_str] = []
        organized[dest_str].append(meta['path'])

    return organized


def organize_by_dimensions(
    metadata_list: list[dict],
    output_dir: str,
    copy_mode: bool = True,
    dry_run: bool = False
) -> dict[str, list[str]]:
    """Organize images by aspect ratio/orientation."""
    output_path = Path(output_dir)
    organized = {}

    for meta in metadata_list:
        width, height = meta['width'], meta['height']

        # Determine orientation
        if abs(width - height) / max(width, height) < 0.1:
            category = 'square'
        elif width > height:
            category = 'landscape'
        else:
            category = 'portrait'

        orient_dir = output_path / category

        if not dry_run:
            orient_dir.mkdir(parents=True, exist_ok=True)

        dest = orient_dir / meta['filename']

        if dry_run:
            dest_str = str(dest)
        else:
            if copy_mode:
                shutil.copy2(meta['path'], dest)
            else:
                shutil.move(meta['path'], dest)
            dest_str = str(dest)

        if dest_str not in organized:
            organized[dest_str] = []
        organized[dest_str].append(meta['path'])

    return organized


def organize_by_color(
    metadata_list: list[dict],
    output_dir: str,
    copy_mode: bool = True,
    dry_run: bool = False
) -> dict[str, list[str]]:
    """Organize images by dominant color."""
    output_path = Path(output_dir)
    organized = {}

    for meta in metadata_list:
        color = meta.get('color', 'other')
        color_dir = output_path / color

        if not dry_run:
            color_dir.mkdir(parents=True, exist_ok=True)

        dest = color_dir / meta['filename']

        if dry_run:
            dest_str = str(dest)
        else:
            if copy_mode:
                shutil.copy2(meta['path'], dest)
            else:
                shutil.move(meta['path'], dest)
            dest_str = str(dest)

        if dest_str not in organized:
            organized[dest_str] = []
        organized[dest_str].append(meta['path'])

    return organized


def organize_images(
    input_dir: str,
    output_dir: str,
    organize_by: str = 'date',
    copy_mode: bool = True,
    dry_run: bool = False,
    verbose: bool = False
) -> dict[str, list[str]]:
    """
    Organize images in a directory.

    Args:
        input_dir: Path to input directory.
        output_dir: Path to output directory.
        organize_by: Organization criterion (date/size/dimensions/color).
        copy_mode: Copy files (True) or move them (False).
        dry_run: Preview without making changes.
        verbose: Print progress information.

    Returns:
        Dictionary mapping destination paths to source paths.
    """
    input_path = Path(input_dir)
    image_files = [f for f in input_path.iterdir() if f.suffix.lower() in SUPPORTED_FORMATS]

    if verbose:
        print(f"Found {len(image_files)} images")

    # Get metadata for all images
    metadata_list = []
    for img_file in image_files:
        if verbose:
            print(f"Analyzing: {img_file.name}")
        try:
            meta = get_image_metadata(str(img_file))
            metadata_list.append(meta)
        except Exception as e:
            print(f"Error analyzing {img_file.name}: {e}")

    # Organize
    if organize_by == 'date':
        organized = organize_by_date(metadata_list, output_dir, copy_mode, dry_run)
    elif organize_by == 'size':
        organized = organize_by_size(metadata_list, output_dir, copy_mode, dry_run)
    elif organize_by == 'dimensions':
        organized = organize_by_dimensions(metadata_list, output_dir, copy_mode, dry_run)
    elif organize_by == 'color':
        organized = organize_by_color(metadata_list, output_dir, copy_mode, dry_run)
    else:
        raise ValueError(f"Unknown organization criterion: {organize_by}")

    return organized


def main():
    parser = argparse.ArgumentParser(
        description="Organize images into folders by date, size, dimensions, or color."
    )
    parser.add_argument(
        "-i", "--input",
        type=str,
        required=True,
        help="Input directory containing images"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        required=True,
        help="Output directory for organized images"
    )
    parser.add_argument(
        "-b", "--by",
        type=str,
        choices=['date', 'size', 'dimensions', 'color'],
        default='date',
        help="Organization criterion (default: date)"
    )
    parser.add_argument(
        "--move",
        action="store_true",
        help="Move files instead of copying"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without making them"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print progress information"
    )

    args = parser.parse_args()

    print(f"Organizing images by {args.by}...")
    if args.dry_run:
        print("(DRY RUN - no changes will be made)")

    try:
        organized = organize_images(
            args.input,
            args.output,
            organize_by=args.by,
            copy_mode=not args.move,
            dry_run=args.dry_run,
            verbose=args.verbose
        )

        if args.dry_run:
            print(f"\nWould organize {len(organized)} images:")
            for dest, sources in organized.items():
                for src in sources:
                    print(f"  {src} -> {dest}")
        else:
            print(f"\nOrganized {len(organized)} images to {args.output}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()