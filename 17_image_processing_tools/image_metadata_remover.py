#!/usr/bin/env python3
"""
Image Metadata Remover Tool
Strip all EXIF/metadata from images to protect your personal information.

Removes: GPS location, device info, date taken, software, author, and all
other embedded metadata — leaving only the visual pixel data.

Usage:
    python image_metadata_remover.py -i photo.jpg -o clean_photo.jpg
    python image_metadata_remover.py -i photo.jpg --in-place
    python image_metadata_remover.py -d photos/ -o cleaned/
    python image_metadata_remover.py -d photos/ --in-place
    python image_metadata_remover.py -i photo.jpg --verify
"""

import argparse
import shutil
from io import BytesIO
from pathlib import Path
from PIL import Image


SUPPORTED_FORMATS = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff', '.tif')


# ─────────────────────────────────────────────
# Core removal logic
# ─────────────────────────────────────────────

def _has_metadata(image_path: str) -> bool:
    """Check whether an image contains any EXIF/metadata."""
    img = Image.open(image_path)
    try:
        if hasattr(img, '_getexif') and img._getexif():
            return True
    except Exception:
        pass
    if img.info:
        # Filter out benign non-personal info keys
        sensitive_keys = {k for k in img.info if k.lower() not in ('dpi',)}
        if sensitive_keys:
            return True
    return False


def remove_metadata(
    input_path: str,
    output_path: str,
    quality: int = 95,
    verbose: bool = False
) -> dict:
    """
    Remove all EXIF and embedded metadata from an image.

    The image is re-encoded through a clean in-memory buffer so no
    metadata is carried forward — only pixel data is preserved.

    Args:
        input_path:  Path to the source image.
        output_path: Path to save the cleaned image.
        quality:     Quality for lossy formats (JPEG/WEBP). Default: 95
                     (high quality — use lower only if file size matters).
        verbose:     Print what was found and removed.

    Returns:
        Dict with 'input', 'output', 'had_metadata', 'size_before', 'size_after'.
    """
    img = Image.open(input_path)
    fmt = img.format or Path(output_path).suffix.lstrip('.').upper()
    if fmt.upper() == 'JPG':
        fmt = 'JPEG'

    # Detect metadata presence before stripping
    had_metadata = False
    stripped_fields = []

    try:
        exif = img._getexif()
        if exif:
            from PIL.ExifTags import TAGS
            had_metadata = True
            for tag_id, val in exif.items():
                tag_name = TAGS.get(tag_id, str(tag_id))
                stripped_fields.append(tag_name)
    except Exception:
        pass

    if img.info:
        for k in img.info:
            if k.lower() not in ('dpi',):
                had_metadata = True
                stripped_fields.append(k)

    size_before = Path(input_path).stat().st_size

    # ── Core strip: re-encode via a clean buffer with no metadata ──
    # Convert mode if needed for the target format
    if fmt.upper() == 'JPEG' and img.mode in ('RGBA', 'P', 'LA'):
        # JPEG doesn't support transparency — composite on white
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        if img.mode in ('RGBA', 'LA'):
            background.paste(img, mask=img.split()[-1])
        img = background
    elif fmt.upper() in ('PNG', 'WEBP') and img.mode == 'P':
        img = img.convert('RGBA')

    # Build save kwargs — do NOT pass exif= or any metadata
    save_kwargs: dict = {}
    if fmt.upper() in ('JPEG', 'WEBP'):
        save_kwargs['quality'] = quality
        save_kwargs['optimize'] = True
    elif fmt.upper() == 'PNG':
        save_kwargs['optimize'] = True

    # Write to buffer first to ensure no original file handle leaks metadata
    buffer = BytesIO()
    img.save(buffer, format=fmt.upper(), **save_kwargs)
    buffer.seek(0)

    # Write clean image to output
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(buffer.read())

    size_after = Path(output_path).stat().st_size

    if verbose:
        if had_metadata:
            print(f"  Stripped {len(stripped_fields)} metadata field(s): "
                  f"{', '.join(stripped_fields[:8])}"
                  f"{'...' if len(stripped_fields) > 8 else ''}")
        else:
            print("  No metadata found in this image.")

    return {
        'input':         input_path,
        'output':        output_path,
        'had_metadata':  had_metadata,
        'stripped_fields': stripped_fields,
        'size_before':   size_before,
        'size_after':    size_after,
    }


def remove_metadata_directory(
    input_dir: str,
    output_dir: str,
    in_place: bool = False,
    quality: int = 95,
    verbose: bool = False
) -> list[dict]:
    """
    Remove metadata from all images in a directory.

    Args:
        input_dir:  Source directory.
        output_dir: Destination directory for cleaned images.
        in_place:   Overwrite originals instead of saving to output_dir.
        quality:    Quality for lossy formats.
        verbose:    Print per-file progress.

    Returns:
        List of result dicts from remove_metadata().
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir) if not in_place else None
    if output_path:
        output_path.mkdir(parents=True, exist_ok=True)

    image_files = sorted(
        f for f in input_path.iterdir()
        if f.suffix.lower() in SUPPORTED_FORMATS
    )

    results = []
    for img_file in image_files:
        if in_place:
            dest = str(img_file)
        else:
            dest = str(output_path / img_file.name)

        if verbose:
            print(f"Processing: {img_file.name}")

        try:
            result = remove_metadata(str(img_file), dest, quality=quality, verbose=verbose)
            results.append(result)
        except Exception as e:
            print(f"  Error processing {img_file.name}: {e}")

    return results


def verify_clean(image_path: str) -> tuple[bool, list[str]]:
    """
    Verify that an image has no remaining EXIF metadata.

    Args:
        image_path: Path to image to check.

    Returns:
        Tuple of (is_clean: bool, remaining_fields: list[str]).
    """
    img = Image.open(image_path)
    remaining = []

    try:
        exif = img._getexif()
        if exif:
            from PIL.ExifTags import TAGS
            for tag_id in exif:
                remaining.append(TAGS.get(tag_id, str(tag_id)))
    except Exception:
        pass

    for k in img.info:
        if k.lower() not in ('dpi',):
            remaining.append(k)

    return len(remaining) == 0, remaining


def _format_size(size_bytes: int) -> str:
    """Format bytes as human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Strip all EXIF/metadata from images to protect your personal information.\n\n"
            "Removes: GPS location, device make/model, date taken, software,\n"
            "author, copyright, and all other embedded metadata.\n"
            "Only the visual pixel data is preserved."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter
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
        help="Output file or directory (not needed with --in-place)"
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite the original file(s) directly. WARNING: original data will be lost."
    )
    parser.add_argument(
        "-q", "--quality",
        type=int,
        default=95,
        help="Quality for JPEG/WEBP output (1-100, default: 95)"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="After cleaning, verify the output has no remaining metadata"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print what metadata was stripped from each file"
    )

    args = parser.parse_args()

    if not args.input and not args.directory:
        parser.error("Either --input or --directory is required")

    if not args.in_place and not args.output:
        parser.error("Either --output or --in-place is required")

    if args.in_place and args.output:
        parser.error("--in-place and --output cannot be used together")

    # ── Single file ──
    if args.input:
        output_path = args.input if args.in_place else args.output
        print(f"Cleaning: {args.input}")

        result = remove_metadata(args.input, output_path, quality=args.quality, verbose=args.verbose)

        if result['had_metadata']:
            size_diff = result['size_before'] - result['size_after']
            sign = '-' if size_diff > 0 else '+'
            print(f"  [DONE] Metadata removed ({len(result['stripped_fields'])} fields stripped)")
            print(f"  Size: {_format_size(result['size_before'])} -> {_format_size(result['size_after'])} "
                  f"({sign}{_format_size(abs(size_diff))})")
        else:
            print("  [INFO] No metadata found - image was already clean")
        print(f"  Saved to: {output_path}")

        if args.verify:
            is_clean, remaining = verify_clean(output_path)
            if is_clean:
                print("  [SAFE] Verified: image is clean - no metadata remaining")
            else:
                print(f"  [WARN] Warning: {len(remaining)} field(s) still present: {remaining}")

    # ── Batch directory ──
    elif args.directory:
        output_dir = args.directory if args.in_place else args.output
        if args.in_place:
            print(f"Cleaning in-place: {args.directory}")
        else:
            print(f"Cleaning: {args.directory}  →  {output_dir}")

        results = remove_metadata_directory(
            args.directory,
            output_dir,
            in_place=args.in_place,
            quality=args.quality,
            verbose=args.verbose
        )

        # Summary
        cleaned  = sum(1 for r in results if r['had_metadata'])
        skipped  = sum(1 for r in results if not r['had_metadata'])
        total_before = sum(r['size_before'] for r in results)
        total_after  = sum(r['size_after']  for r in results)

        print(f"\n{'-' * 44}")
        print(f"  Processed : {len(results)} images")
        print(f"  Cleaned   : {cleaned} (had metadata)")
        print(f"  Already clean: {skipped}")
        saved = total_before - total_after
        if saved > 0:
            print(f"  Total size : {_format_size(total_before)} -> {_format_size(total_after)} "
                  f"(-{_format_size(saved)} saved)")
        print(f"{'-' * 44}")

        if args.verify:
            fail_count = 0
            for r in results:
                is_clean, remaining = verify_clean(r['output'])
                if not is_clean:
                    fail_count += 1
                    print(f"  [WARN] {Path(r['output']).name}: still has {remaining}")
            if fail_count == 0:
                print("  [SAFE] All images verified clean.")


if __name__ == "__main__":
    main()
