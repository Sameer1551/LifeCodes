#!/usr/bin/env python3
"""
file_tools.py

A robust, offline-capable toolbox for common file-system tasks.

Features:
* Text extraction (PDF, DOCX, TXT, Image-OCR)
* Bulk extraction & conversion
* Bulk renaming with pattern support
* Folder organization (by extension, date, size)
* Duplicate detection (hash-based) with optional quarantine
* Compression / archive extraction

Dependencies:
    pip install PyPDF2 python-docx pillow tqdm
    (Optional for OCR: pip install pytesseract)
"""

import argparse
import hashlib
import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Tuple, Union

# ----------------------------------------------------------------------
# Optional third-party imports
# ----------------------------------------------------------------------
try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None

try:
    import docx
except Exception:
    docx = None

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:
    Image = None

try:
    import pytesseract
except Exception:
    pytesseract = None

try:
    from tqdm import tqdm
except Exception:
    # Fallback iterator if tqdm is not installed
    def tqdm(iterable, **kwargs):
        return iterable

# ----------------------------------------------------------------------
# Logging configuration
# ----------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Helper utilities
# ----------------------------------------------------------------------
def _as_path(p: Union[Path, str]) -> Path:
    """Coerce a string or pathlib.Path to an absolute pathlib.Path."""
    return Path(p).expanduser().resolve()


def _hash_file(file_path: Path, algo: str = "md5", chunk_size: int = 8192) -> str:
    """Return a hex digest of *file_path* using the selected hash algorithm."""
    h = hashlib.new(algo)
    try:
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                h.update(chunk)
        return h.hexdigest()
    except PermissionError:
        log.error(f"Permission denied: {file_path}")
        raise

def _ensure_parent_dir(path: Path) -> None:
    """Create parent directories for *path* if they do not exist."""
    path.parent.mkdir(parents=True, exist_ok=True)


# ----------------------------------------------------------------------
# 1️⃣  Text extraction
# ----------------------------------------------------------------------
def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract raw text from a PDF file using PyPDF2."""
    if PdfReader is None:
        raise ImportError("PyPDF2 is required for PDF extraction (pip install PyPDF2)")
    reader = PdfReader(str(pdf_path))
    text = []
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text.append(extracted)
    return "\n".join(text)


def extract_text_from_docx(docx_path: Path) -> str:
    """Extract raw text from a DOCX file using python-docx."""
    if docx is None:
        raise ImportError("python-docx is required for DOCX extraction (pip install python-docx)")
    document = docx.Document(str(docx_path))
    return "\n".join(p.text for p in document.paragraphs)


def extract_text_from_image(img_path: Path) -> str:
    """Run OCR on an image and return the detected text."""
    if pytesseract is None:
        raise ImportError("pytesseract is required for image OCR.")
    if Image is None:
        raise ImportError("Pillow is required for image handling (pip install pillow)")
    
    img = Image.open(str(img_path))
    return pytesseract.image_to_string(img)


def extract_text(file_path: Path) -> str:
    """
    Dispatch helper that extracts plain text from supported file types.
    Supported: .txt, .pdf, .docx, .png, .jpg, .jpeg, .tiff, .bmp, .gif
    """
    suffix = file_path.suffix.lower()
    
    if suffix == ".txt":
        # Added errors='ignore' to handle encoding issues gracefully
        return file_path.read_text(encoding="utf-8", errors="ignore")
    elif suffix == ".pdf":
        return extract_text_from_pdf(file_path)
    elif suffix == ".docx":
        return extract_text_from_docx(file_path)
    elif suffix in {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"}:
        return extract_text_from_image(file_path)
    else:
        raise ValueError(f"Unsupported file type for text extraction: {suffix}")


def bulk_extract_text(
    input_paths: Iterable[Path],
    output_dir: Path,
    overwrite: bool = False,
    progress: bool = True,
) -> List[Path]:
    """
    Extract text from many files and write each result as a ``.txt`` file.
    """
    output_dir = _as_path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    created: List[Path] = []

    files = [_as_path(p) for p in input_paths]
    iterator = tqdm(files, desc="Extracting", disable=not progress)

    for src in iterator:
        if not src.is_file():
            log.warning(f"Skipping non-file: {src}")
            continue

        try:
            txt = extract_text(src)
        except Exception as exc:
            log.error(f"Failed to extract {src} – {exc}")
            continue

        out_path = output_dir / (src.stem + ".txt")
        if out_path.is_file() and not overwrite:
            log.info(f"Skipping existing: {out_path}")
            continue

        _ensure_parent_dir(out_path)
        out_path.write_text(txt, encoding="utf-8")
        created.append(out_path)

    log.info(f"Extracted {len(created)} files to {output_dir}")
    return created


# ----------------------------------------------------------------------
# 2️⃣  Format conversion
# ----------------------------------------------------------------------
def convert_file(input_path: Path, output_path: Path) -> None:
    """
    Simple conversion utility.
    Supported: PDF→TXT, DOCX→TXT, Image→PDF, TXT→PDF.
    """
    input_path = _as_path(input_path)
    output_path = _as_path(output_path)

    in_ext = input_path.suffix.lower()
    out_ext = output_path.suffix.lower()

    # 1) PDF → TXT
    if in_ext == ".pdf" and out_ext == ".txt":
        txt = extract_text_from_pdf(input_path)
        _ensure_parent_dir(output_path)
        output_path.write_text(txt, encoding="utf-8")
        return

    # 2) DOCX → TXT
    if in_ext == ".docx" and out_ext == ".txt":
        txt = extract_text_from_docx(input_path)
        _ensure_parent_dir(output_path)
        output_path.write_text(txt, encoding="utf-8")
        return

    # 3) Image → PDF
    if in_ext in {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"} and out_ext == ".pdf":
        if Image is None:
            raise ImportError("Pillow is required for image → PDF conversion")
        img = Image.open(str(input_path))
        rgb = img.convert("RGB")
        _ensure_parent_dir(output_path)
        rgb.save(str(output_path), "PDF", resolution=100.0)
        return

    # 4) TXT → PDF (Basic implementation using Pillow)
    if in_ext == ".txt" and out_ext == ".pdf":
        if Image is None:
            raise ImportError("Pillow is required for txt → PDF conversion")
        
        txt = input_path.read_text(encoding="utf-8", errors="ignore")
        
        # Simple font handling
        try:
            # Try to load a basic font
            font = ImageFont.truetype("arial.ttf", 14)
        except IOError:
            # Fallback to default
            font = ImageFont.load_default()
        
        lines = txt.splitlines()
        
        # Estimate canvas size (basic heuristic)
        max_width = max(font.getlength(line) if hasattr(font, 'getlength') else len(line)*8 for line in lines) + 20
        line_height = 20
        img_height = line_height * (len(lines) + 2)
        
        canvas = Image.new("RGB", (int(max_width), int(img_height)), "white")
        draw = ImageDraw.Draw(canvas)
        
        y = 10
        for line in lines:
            draw.text((10, y), line, fill="black", font=font)
            y += line_height
            
        _ensure_parent_dir(output_path)
        canvas.save(str(output_path), "PDF")
        return

    raise ValueError(f"Unsupported conversion: {in_ext} → {out_ext}")


def bulk_convert(
    inputs: Iterable[Path],
    output_dir: Path,
    suffix: str,
    overwrite: bool = False,
    progress: bool = True,
) -> List[Path]:
    """Convert a list of files to a common target suffix."""
    output_dir = _as_path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    created: List[Path] = []

    files = [_as_path(p) for p in inputs]
    iterator = tqdm(files, desc="Converting", disable=not progress)

    for src in iterator:
        if not src.is_file():
            continue

        dst = output_dir / (src.stem + suffix)
        if dst.is_file() and not overwrite:
            continue

        try:
            convert_file(src, dst)
            created.append(dst)
        except Exception as exc:
            log.error(f"Conversion failed for {src}: {exc}")

    log.info(f"Created {len(created)} files in {output_dir}")
    return created


# ----------------------------------------------------------------------
# 3️⃣  Bulk renaming
# ----------------------------------------------------------------------
def bulk_rename(
    target_dir: Path,
    pattern: str,
    dry_run: bool = False,
    start_index: int = 1,
) -> List[Tuple[Path, Path]]:
    """
    Rename every file in *target_dir* according to *pattern*.
    Placeholders: {index}, {name}, {ext}
    """
    target_dir = _as_path(target_dir)
    if not target_dir.is_dir():
        raise ValueError(f"{target_dir} is not a directory")

    files = sorted([p for p in target_dir.iterdir() if p.is_file()])
    renamed: List[Tuple[Path, Path]] = []

    for idx, src in enumerate(files, start=start_index):
        new_name = pattern.format(index=idx, name=src.stem, ext=src.suffix)
        dst = src.with_name(new_name)

        if dst.exists():
            log.warning(f"Target exists, skipping: {dst}")
            continue

        if dry_run:
            log.info(f"[DRY-RUN] Would rename: {src.name} -> {new_name}")
        else:
            src.rename(dst)
            log.info(f"Renamed: {src.name} -> {new_name}")

        renamed.append((src, dst))

    return renamed


# ----------------------------------------------------------------------
# 4️⃣  Folder organization
# ----------------------------------------------------------------------
def organize_folder(
    source_dir: Path,
    criteria: str = "extension",
    dry_run: bool = False,
) -> List[Tuple[Path, Path]]:
    """
    Move files from *source_dir* into sub-folders based on *criteria*.
    Supported: 'extension', 'date', 'size'
    """
    source_dir = _as_path(source_dir)
    if not source_dir.is_dir():
        raise ValueError(f"{source_dir} is not a directory")

    moves: List[Tuple[Path, Path]] = []

    # Size buckets
    size_bins = {
        "small": (0, 1_000_000),
        "medium": (1_000_000, 10_000_000),
        "large": (10_000_000, float("inf")),
    }

    for src in source_dir.iterdir():
        if not src.is_file():
            continue

        subfolder = "unknown"

        if criteria == "extension":
            subfolder = src.suffix.lstrip(".").lower() or "no_ext"
        
        elif criteria == "date":
            # FIX: Use datetime to handle timestamp
            ts = src.stat().st_mtime
            subfolder = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
        
        elif criteria == "size":
            size = src.stat().st_size
            for label, (low, high) in size_bins.items():
                if low <= size < high:
                    subfolder = label
                    break

        dst_dir = source_dir / subfolder
        dst = dst_dir / src.name

        if dst.exists():
            log.warning(f"Destination exists, skipping: {dst}")
            continue

        if dry_run:
            log.info(f"[DRY-RUN] Would move: {src.name} -> {subfolder}/")
        else:
            dst_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            log.info(f"Moved: {src.name} -> {subfolder}/")

        moves.append((src, dst))

    return moves


# ----------------------------------------------------------------------
# 5️⃣  Duplicate detection
# ----------------------------------------------------------------------
def find_duplicates(
    root_dir: Path,
    hash_algo: str = "md5",
    min_size: int = 1,
) -> dict[str, List[Path]]:
    """
    Walk *root_dir* and return a mapping ``hash -> [paths...]`` for
    files with identical content.
    """
    root_dir = _as_path(root_dir)
    if not root_dir.is_dir():
        raise ValueError(f"{root_dir} is not a directory")

    hash_map: dict[str, List[Path]] = {}
    
    # Use rglob to walk recursively
    for file_path in root_dir.rglob("*"):
        if not file_path.is_file():
            continue
        
        # Optimization: Skip very small files if requested
        if file_path.stat().st_size < min_size:
            continue

        try:
            file_hash = _hash_file(file_path, algo=hash_algo)
            hash_map.setdefault(file_hash, []).append(file_path)
        except Exception as e:
            log.warning(f"Could not hash {file_path}: {e}")

    # Filter to keep only duplicates
    duplicates = {h: paths for h, paths in hash_map.items() if len(paths) > 1}
    log.info(f"Found {len(duplicates)} groups of duplicates.")
    return duplicates


def print_duplicate_report(duplicates: dict[str, List[Path]]) -> None:
    """Pretty-print duplicate groups."""
    if not duplicates:
        print("✅ No duplicate files found.")
        return

    print("\n⚠️ Duplicate files detected:")
    for h, paths in duplicates.items():
        print(f"\nHash: {h}")
        for p in paths:
            print(f"  • {p}")
    print()


def move_duplicates(duplicates: dict[str, List[Path]], dest_dir: Path) -> None:
    """
    Move duplicate files (keeping one copy) to a quarantine folder.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    count = 0
    for paths in duplicates.values():
        # Keep the first file found, move the rest
        for p in paths[1:]:
            try:
                target = dest_dir / p.name
                # Handle name collisions in quarantine
                if target.exists():
                    target = dest_dir / f"{p.stem}_{p.stat().st_size}{p.suffix}"
                
                shutil.move(str(p), str(target))
                log.info(f"Quarantined duplicate: {p}")
                count += 1
            except Exception as e:
                log.error(f"Failed to move {p}: {e}")
    
    log.info(f"Moved {count} duplicate files to {dest_dir}")


# ----------------------------------------------------------------------
# 6️⃣  Compression & archive handling
# ----------------------------------------------------------------------
def compress_to_zip(file_paths: Iterable[Path], archive_path: Path) -> None:
    """Create a ZIP archive."""
    from zipfile import ZipFile, ZIP_DEFLATED

    archive_path = _as_path(archive_path)
    if archive_path.suffix.lower() != ".zip":
        archive_path = archive_path.with_suffix(".zip")

    _ensure_parent_dir(archive_path)
    
    with ZipFile(str(archive_path), "w", compression=ZIP_DEFLATED) as zipf:
        for path in file_paths:
            p = _as_path(path)
            if p.is_file():
                zipf.write(str(p), arcname=p.name)
                log.info(f"Added to zip: {p.name}")

    log.info(f"Archive created at {archive_path}")


def extract_archive(archive_path: Path, dest_dir: Path) -> None:
    """Extract any archive supported by shutil.unpack_archive."""
    archive_path = _as_path(archive_path)
    dest_dir = _as_path(dest_dir)

    if not archive_path.is_file():
        raise ValueError(f"{archive_path} does not exist")

    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.unpack_archive(str(archive_path), str(dest_dir))
    log.info(f"Extracted {archive_path} → {dest_dir}")


# ----------------------------------------------------------------------
# Command-line interface
# ----------------------------------------------------------------------
def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Offline Developer Toolkit - File Tools",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Extract
    p_ex = subparsers.add_parser("extract", help="Extract text from a file")
    p_ex.add_argument("input", type=_as_path)
    p_ex.add_argument("output", type=_as_path)

    # Bulk Extract
    p_bulk_ex = subparsers.add_parser("bulk-extract", help="Extract text from multiple files")
    p_bulk_ex.add_argument("inputs", nargs="+", type=_as_path)
    p_bulk_ex.add_argument("-o", "--output-dir", type=_as_path, required=True)
    p_bulk_ex.add_argument("--overwrite", action="store_true")
    p_bulk_ex.add_argument("--no-progress", action="store_true")

    # Convert
    p_conv = subparsers.add_parser("convert", help="Convert file format")
    p_conv.add_argument("input", type=_as_path)
    p_conv.add_argument("output", type=_as_path)

    # Bulk Convert
    p_bulk_conv = subparsers.add_parser("bulk-convert", help="Convert multiple files")
    p_bulk_conv.add_argument("inputs", nargs="+", type=_as_path)
    p_bulk_conv.add_argument("-s", "--suffix", required=True, help="Target extension (e.g. .pdf)")
    p_bulk_conv.add_argument("-o", "--output-dir", type=_as_path, required=True)
    p_bulk_conv.add_argument("--overwrite", action="store_true")

    # Rename
    p_rename = subparsers.add_parser("rename", help="Bulk rename files")
    p_rename.add_argument("directory", type=_as_path)
    p_rename.add_argument("pattern", help="Pattern: {name}{ext}{index}")
    p_rename.add_argument("--dry-run", action="store_true")
    p_rename.add_argument("--start-index", type=int, default=1)

    # Organize
    p_org = subparsers.add_parser("organize", help="Organize folder by criteria")
    p_org.add_argument("directory", type=_as_path)
    p_org.add_argument("-c", "--criteria", choices=["extension", "date", "size"], default="extension")
    p_org.add_argument("--dry-run", action="store_true")

    # Duplicates
    p_dupes = subparsers.add_parser("find-dupes", help="Find duplicate files")
    p_dupes.add_argument("directory", type=_as_path)
    p_dupes.add_argument("-a", "--algo", default="md5")
    p_dupes.add_argument("-m", "--min-size", type=int, default=1)
    p_dupes.add_argument("--move-to", type=_as_path, help="Move duplicates to this folder")
    p_dupes.add_argument("--print", action="store_true", dest="do_print")

    # Zip
    p_zip = subparsers.add_parser("zip", help="Compress files")
    p_zip.add_argument("archive", type=_as_path)
    p_zip.add_argument("files", nargs="+", type=_as_path)

    # Unzip
    p_unzip = subparsers.add_parser("unzip", help="Extract archive")
    p_unzip.add_argument("archive", type=_as_path)
    p_unzip.add_argument("-d", "--dest", type=_as_path, required=True)

    return parser


def main() -> None:
    parser = _build_cli_parser()
    args = parser.parse_args()

    try:
        if args.command == "extract":
            out = extract_text(args.input)
            _ensure_parent_dir(args.output)
            args.output.write_text(out, encoding="utf-8")
            log.info(f"Extracted text to {args.output}")

        elif args.command == "bulk-extract":
            bulk_extract_text(args.inputs, args.output_dir, args.overwrite, not args.no_progress)

        elif args.command == "convert":
            convert_file(args.input, args.output)

        elif args.command == "bulk-convert":
            bulk_convert(args.inputs, args.output_dir, args.suffix, args.overwrite)

        elif args.command == "rename":
            bulk_rename(args.directory, args.pattern, args.dry_run, args.start_index)

        elif args.command == "organize":
            organize_folder(args.directory, args.criteria, args.dry_run)

        elif args.command == "find-dupes":
            dupes = find_duplicates(args.directory, args.algo, args.min_size)
            if args.move_to:
                move_duplicates(dupes, args.move_to)
            elif args.do_print:
                print_duplicate_report(dupes)
            else:
                log.info(f"Found {len(dupes)} duplicate groups. Use --print or --move-to to see results.")

        elif args.command == "zip":
            compress_to_zip(args.files, args.archive)

        elif args.command == "unzip":
            extract_archive(args.archive, args.dest)

    except Exception as e:
        log.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
