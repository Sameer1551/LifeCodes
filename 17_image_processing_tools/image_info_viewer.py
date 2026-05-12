#!/usr/bin/env python3
"""
Image Info Viewer Tool
View all metadata stored inside an image file in a clean, human-readable format.
Highlights personal/sensitive information such as GPS location, device info, and dates.

Usage:
    python image_info_viewer.py -i photo.jpg
    python image_info_viewer.py -i photo.jpg --json
    python image_info_viewer.py -d photos/ --privacy-check
"""

import argparse
import json
import math
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS


SUPPORTED_FORMATS = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff', '.tif')


# ─────────────────────────────────────────────
# Raw EXIF extraction
# ─────────────────────────────────────────────

def _extract_raw_exif(image_path: str) -> dict:
    """Extract raw EXIF data using Pillow."""
    img = Image.open(image_path)
    raw = {}

    try:
        exif_data = img._getexif()
        if exif_data:
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, str(tag_id))
                if tag == 'GPSInfo' and isinstance(value, dict):
                    gps = {}
                    for gps_id, gps_val in value.items():
                        gps_tag = GPSTAGS.get(gps_id, str(gps_id))
                        gps[gps_tag] = gps_val
                    raw['GPSInfo'] = gps
                else:
                    raw[tag] = value
    except Exception:
        pass

    return raw


def _rational_to_float(rational) -> float:
    """Convert an EXIF rational (tuple or IFDRational) to a float."""
    try:
        if isinstance(rational, tuple):
            return rational[0] / rational[1] if rational[1] != 0 else 0.0
        return float(rational)
    except Exception:
        return 0.0


def _dms_to_decimal(dms, ref: str) -> float:
    """Convert GPS degrees/minutes/seconds to decimal degrees."""
    try:
        degrees = _rational_to_float(dms[0])
        minutes = _rational_to_float(dms[1])
        seconds = _rational_to_float(dms[2])
        decimal = degrees + minutes / 60 + seconds / 3600
        if ref in ('S', 'W'):
            decimal = -decimal
        return round(decimal, 6)
    except Exception:
        return 0.0


# ─────────────────────────────────────────────
# Structured info extraction
# ─────────────────────────────────────────────

def get_image_info(image_path: str) -> dict:
    """
    Extract and structure all available metadata from an image.

    Args:
        image_path: Path to the image file.

    Returns:
        Dictionary with structured metadata grouped by category.
    """
    path = Path(image_path)
    img = Image.open(image_path)
    stat = path.stat()

    info = {
        'file': {
            'filename':   path.name,
            'filepath':   str(path.resolve()),
            'format':     img.format or path.suffix.lstrip('.').upper(),
            'mode':       img.mode,
            'width_px':   img.width,
            'height_px':  img.height,
            'file_size':  _format_size(stat.st_size),
            'file_size_bytes': stat.st_size,
        },
        'camera': {},
        'location': {},
        'dates': {},
        'software': {},
        'other': {},
        'privacy_risks': [],
    }

    raw = _extract_raw_exif(image_path)
    if not raw:
        return info

    # ── Camera / Device ──
    for field, label in [
        ('Make',             'camera_make'),
        ('Model',            'camera_model'),
        ('LensMake',         'lens_make'),
        ('LensModel',        'lens_model'),
        ('ExposureTime',     'exposure_time'),
        ('FNumber',          'f_number'),
        ('ISOSpeedRatings',  'iso'),
        ('FocalLength',      'focal_length_mm'),
        ('Flash',            'flash'),
        ('WhiteBalance',     'white_balance'),
        ('MeteringMode',     'metering_mode'),
        ('ExposureMode',     'exposure_mode'),
        ('SceneCaptureType', 'scene_type'),
        ('DigitalZoomRatio', 'digital_zoom'),
    ]:
        val = raw.get(field)
        if val is not None:
            if field in ('ExposureTime',):
                try:
                    val = f"1/{int(1/_rational_to_float(val))}s"
                except Exception:
                    val = str(val)
            elif field in ('FNumber', 'FocalLength', 'DigitalZoomRatio'):
                val = round(_rational_to_float(val), 2)
            info['camera'][label] = val

    # ── GPS / Location ──
    gps = raw.get('GPSInfo', {})
    if gps:
        lat_dms = gps.get('GPSLatitude')
        lat_ref = gps.get('GPSLatitudeRef', 'N')
        lon_dms = gps.get('GPSLongitude')
        lon_ref = gps.get('GPSLongitudeRef', 'E')
        alt_raw = gps.get('GPSAltitude')
        alt_ref = gps.get('GPSAltitudeRef', 0)

        if lat_dms and lon_dms:
            lat = _dms_to_decimal(lat_dms, lat_ref)
            lon = _dms_to_decimal(lon_dms, lon_ref)
            info['location'] = {
                'latitude':     lat,
                'longitude':    lon,
                'maps_link':    f"https://maps.google.com/?q={lat},{lon}",
            }
            if alt_raw is not None:
                alt = _rational_to_float(alt_raw)
                if alt_ref == 1:
                    alt = -alt
                info['location']['altitude_m'] = round(alt, 1)
            info['privacy_risks'].append(
                f"[WARN] GPS coordinates embedded: {lat}, {lon} -> {info['location']['maps_link']}"
            )

    # ── Dates ──
    for field, label in [
        ('DateTimeOriginal', 'date_taken'),
        ('DateTimeDigitized','date_digitized'),
        ('DateTime',         'date_modified'),
    ]:
        val = raw.get(field)
        if val:
            info['dates'][label] = str(val)
    if info['dates']:
        info['privacy_risks'].append(
            f"[DATE] Date/time embedded: {list(info['dates'].values())[0]}"
        )

    # ── Device / Software ──
    for field, label in [
        ('Software',          'software'),
        ('HostComputer',      'computer_name'),
        ('Artist',            'artist'),
        ('Copyright',         'copyright'),
        ('ImageDescription',  'description'),
        ('UserComment',       'user_comment'),
    ]:
        val = raw.get(field)
        if val:
            info['software'][label] = str(val).strip()
            if label in ('computer_name', 'artist', 'user_comment'):
                info['privacy_risks'].append(
                    f"[USER] Personal field '{label}': {str(val).strip()[:60]}"
                )

    # ── Other EXIF fields ──
    known_fields = {
        'Make', 'Model', 'LensMake', 'LensModel', 'ExposureTime', 'FNumber',
        'ISOSpeedRatings', 'FocalLength', 'Flash', 'WhiteBalance', 'MeteringMode',
        'ExposureMode', 'SceneCaptureType', 'DigitalZoomRatio', 'GPSInfo',
        'DateTimeOriginal', 'DateTimeDigitized', 'DateTime', 'Software',
        'HostComputer', 'Artist', 'Copyright', 'ImageDescription', 'UserComment',
        'ExifImageWidth', 'ExifImageHeight', 'Orientation', 'ResolutionUnit',
        'XResolution', 'YResolution',
    }
    for key, val in raw.items():
        if key not in known_fields:
            try:
                info['other'][key] = str(val)[:120]
            except Exception:
                pass

    if not info['privacy_risks']:
        info['privacy_risks'].append('[SAFE] No obvious personal/sensitive data found.')

    return info


def _format_size(size_bytes: int) -> str:
    """Format bytes as human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


# ─────────────────────────────────────────────
# Output formatting
# ─────────────────────────────────────────────

def format_info_human(info: dict, privacy_only: bool = False) -> str:
    """Format image info as a clean human-readable string."""
    lines = []

    def section(title: str):
        lines.append(f"\n{'-' * 44}")
        lines.append(f"  {title}")
        lines.append('-' * 44)

    def row(label: str, value):
        if value not in (None, '', {}, []):
            lines.append(f"  {label:<22}: {value}")

    # File Info
    section("FILE INFO")
    f = info['file']
    row("Filename",       f['filename'])
    row("Format",         f['format'])
    row("Dimensions",     f"{f['width_px']} × {f['height_px']} px")
    row("Color Mode",     f['mode'])
    row("File Size",      f['file_size'])

    if not privacy_only:
        # Camera
        if info['camera']:
            section("CAMERA / DEVICE")
            cam = info['camera']
            if 'camera_make' in cam or 'camera_model' in cam:
                row("Device",   f"{cam.get('camera_make','')} {cam.get('camera_model','')}".strip())
            if 'lens_model' in cam:
                row("Lens",         cam['lens_model'])
            row("Exposure",         cam.get('exposure_time'))
            row("Aperture",         f"f/{cam['f_number']}" if 'f_number' in cam else None)
            row("ISO",              cam.get('iso'))
            row("Focal Length",     f"{cam['focal_length_mm']}mm" if 'focal_length_mm' in cam else None)
            row("Flash",            cam.get('flash'))

        # Dates
        if info['dates']:
            section("DATES")
            for label, val in info['dates'].items():
                row(label.replace('_', ' ').title(), val)

        # Software
        if info['software']:
            section("SOFTWARE / AUTHOR")
            for label, val in info['software'].items():
                row(label.replace('_', ' ').title(), val)

        # Location
        if info['location']:
            section("GPS LOCATION")
            loc = info['location']
            row("Latitude",     loc.get('latitude'))
            row("Longitude",    loc.get('longitude'))
            if 'altitude_m' in loc:
                row("Altitude",     f"{loc['altitude_m']} m")
            row("Maps Link",    loc.get('maps_link'))

        # Other
        if info['other']:
            section("OTHER EXIF FIELDS")
            for key, val in list(info['other'].items())[:20]:
                row(key, val)

    # Privacy Risks
    section("PRIVACY RISK SUMMARY")
    for risk in info['privacy_risks']:
        lines.append(f"  {risk}")
    if not info['location'] and not privacy_only:
        lines.append("  [SAFE] No GPS data found.")

    lines.append("")
    return "\n".join(lines)


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description=(
            "View all metadata stored in an image file.\n"
            "Highlights personal info: GPS location, device, dates, author fields."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "-i", "--input",
        type=str,
        help="Input image file to inspect"
    )
    parser.add_argument(
        "-d", "--directory",
        type=str,
        help="Directory of images to scan (batch mode)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format"
    )
    parser.add_argument(
        "--privacy-check",
        action="store_true",
        help="Show only the privacy risk summary (quick scan)"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Save output to a file"
    )

    args = parser.parse_args()

    if not args.input and not args.directory:
        parser.error("Either --input or --directory is required")

    results = []

    if args.directory:
        dir_path = Path(args.directory)
        image_files = [f for f in dir_path.iterdir() if f.suffix.lower() in SUPPORTED_FORMATS]
        if not image_files:
            print(f"No supported image files found in: {args.directory}")
            return
        for img_file in sorted(image_files):
            try:
                info = get_image_info(str(img_file))
                results.append(info)
            except Exception as e:
                print(f"Error reading {img_file.name}: {e}")
    else:
        try:
            info = get_image_info(args.input)
            results.append(info)
        except Exception as e:
            print(f"Error: {e}")
            return

    # Format output
    if args.json:
        # Make JSON-serializable
        def clean(obj):
            if isinstance(obj, bytes):
                return obj.hex()
            if isinstance(obj, tuple):
                return list(obj)
            return str(obj)
        output = json.dumps(results if len(results) > 1 else results[0],
                            indent=2, default=clean)
    else:
        parts = []
        for info in results:
            parts.append(format_info_human(info, privacy_only=args.privacy_check))
        output = "\n".join(parts)
        if len(results) > 1:
            output = f"Scanned {len(results)} images\n" + output

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"Results saved to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
