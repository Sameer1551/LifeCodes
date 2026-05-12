#!/usr/bin/env python3
"""
Image to Text OCR Tool
Extract text from images using OCR (Optical Character Recognition).
"""

import argparse
import json
from pathlib import Path
from PIL import Image

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

try:
    from pdf2image import convert_from_path
    HAS_PDF2IMAGE = True
except ImportError:
    HAS_PDF2IMAGE = False


SUPPORTED_FORMATS = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff', '.gif')
SUPPORTED_PDF = ('.pdf',)


def check_tesseract_installed() -> bool:
    """Check if Tesseract OCR is installed."""
    if not HAS_TESSERACT:
        return False
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def preprocess_image(img: Image.Image) -> Image.Image:
    """Preprocess image for better OCR results."""
    # Convert to grayscale
    if img.mode != 'L':
        img = img.convert('L')

    # Increase contrast (simple thresholding)
    img = img.point(lambda x: 0 if x < 128 else 255, '1')

    return img


def extract_text(
    image_path: str,
    lang: str = 'eng',
    preprocess: bool = False,
    bounding_boxes: bool = False
) -> str | list[dict]:
    """
    Extract text from an image using OCR.

    Args:
        image_path: Path to image file.
        lang: Language code (eng, fra, deu, etc.).
        preprocess: Apply preprocessing for better results.
        bounding_boxes: Return text with bounding box coordinates.

    Returns:
        Extracted text or list of dictionaries with text and coordinates.
    """
    if not check_tesseract_installed():
        raise RuntimeError(
            "Tesseract OCR is not installed or not in PATH. "
            "Install from: https://github.com/tesseract-ocr/tesseract"
        )

    img = Image.open(image_path)

    if preprocess:
        img = preprocess_image(img)

    if bounding_boxes:
        # Get bounding boxes for each word
        data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)

        results = []
        n_boxes = len(data['text'])
        for i in range(n_boxes):
            if int(data['conf'][i]) > 0:  # Filter out empty results
                text = data['text'][i].strip()
                if text:
                    results.append({
                        'text': text,
                        'confidence': int(data['conf'][i]),
                        'bbox': {
                            'x': data['left'][i],
                            'y': data['top'][i],
                            'width': data['width'][i],
                            'height': data['height'][i]
                        }
                    })
        return results
    else:
        return pytesseract.image_to_string(img, lang=lang).strip()


def extract_text_from_pdf(
    pdf_path: str,
    lang: str = 'eng',
    preprocess: bool = False
) -> list[dict]:
    """
    Extract text from all pages of a PDF file using OCR.

    Args:
        pdf_path: Path to the PDF file.
        lang: Language code (eng, fra, deu, etc.).
        preprocess: Apply preprocessing for better results.

    Returns:
        List of dicts with 'page' (1-based) and 'text' keys.
    """
    if not HAS_PDF2IMAGE:
        raise ImportError(
            "pdf2image is required for PDF support. Install with: pip install pdf2image\n"
            "Also install poppler: https://github.com/oschwartz10612/poppler-windows/releases (Windows) "
            "or 'apt install poppler-utils' (Linux) or 'brew install poppler' (macOS)"
        )
    if not check_tesseract_installed():
        raise RuntimeError(
            "Tesseract OCR is not installed or not in PATH. "
            "Install from: https://github.com/tesseract-ocr/tesseract"
        )

    pages = convert_from_path(pdf_path)
    results = []
    for page_num, page_img in enumerate(pages, start=1):
        if preprocess:
            page_img = preprocess_image(page_img)
        text = pytesseract.image_to_string(page_img, lang=lang).strip()
        results.append({'page': page_num, 'text': text})
    return results


def extract_text_directory(
    directory: str,
    lang: str = 'eng',
    preprocess: bool = False,
    bounding_boxes: bool = False,
    output_dir: str | None = None,
    verbose: bool = False
) -> dict[str, str | list[dict]]:
    """
    Extract text from all images in a directory.

    Args:
        directory: Path to directory.
        lang: Language code.
        preprocess: Apply preprocessing.
        bounding_boxes: Return with coordinates.
        output_dir: Directory to save text files.
        verbose: Print progress information.

    Returns:
        Dictionary mapping filename to extracted text.
    """
    dir_path = Path(directory)
    image_files = [f for f in dir_path.iterdir()
                   if f.suffix.lower() in SUPPORTED_FORMATS or f.suffix.lower() in SUPPORTED_PDF]

    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

    results = {}

    for img_file in image_files:
        if verbose:
            print(f"Processing: {img_file.name}")

        try:
            if img_file.suffix.lower() in SUPPORTED_PDF:
                # PDF: extract all pages
                pages = extract_text_from_pdf(
                    str(img_file),
                    lang=lang,
                    preprocess=preprocess
                )
                # Combine all pages into a single string
                combined = '\n\n'.join(f"[Page {p['page']}]\n{p['text']}" for p in pages)
                results[img_file.name] = combined
                if output_dir:
                    out_file = output_path / f"{img_file.stem}.txt"
                    with open(out_file, 'w', encoding='utf-8') as f:
                        f.write(combined)
            else:
                text = extract_text(
                    str(img_file),
                    lang=lang,
                    preprocess=preprocess,
                    bounding_boxes=bounding_boxes
                )
                results[img_file.name] = text
                if output_dir and isinstance(text, str):
                    out_file = output_path / f"{img_file.stem}.txt"
                    with open(out_file, 'w', encoding='utf-8') as f:
                        f.write(text)
        except Exception as e:
            print(f"Error processing {img_file.name}: {e}")
            results[img_file.name] = ""

    return results


def format_bounding_boxes_text(results: list[dict]) -> str:
    """Format bounding box results as readable text."""
    lines = []
    for item in results:
        lines.append(f"{item['text']} (conf: {item['confidence']}%)")
        lines.append(f"  bbox: x={item['bbox']['x']}, y={item['bbox']['y']}, "
                    f"w={item['bbox']['width']}, h={item['bbox']['height']}")
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Extract text from images using OCR."
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
        help="Output file or directory"
    )
    parser.add_argument(
        "-l", "--language",
        type=str,
        default='eng',
        help="Language code (default: eng). Common: eng, fra, deu, spa, chi_sim, jpn"
    )
    parser.add_argument(
        "--preprocess",
        action="store_true",
        help="Apply preprocessing (grayscale, threshold) for better OCR"
    )
    parser.add_argument(
        "--bounding-boxes",
        action="store_true",
        help="Output text with bounding box coordinates"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print progress information"
    )
    parser.add_argument(
        "--pdf",
        action="store_true",
        help="Treat input as a PDF file and extract text from all pages"
    )

    args = parser.parse_args()

    if not args.input and not args.directory:
        parser.error("Either --input or --directory is required")

    if not check_tesseract_installed():
        print("Error: Tesseract OCR is not installed.")
        print("Install from: https://github.com/tesseract-ocr/tesseract")
        print("On Windows, add Tesseract to PATH or set pytesseract.pytesseract.tesseract_cmd")
        return

    if args.directory:
        results = extract_text_directory(
            args.directory,
            lang=args.language,
            preprocess=args.preprocess,
            bounding_boxes=args.bounding_boxes,
            output_dir=args.output if args.output else None,
            verbose=args.verbose
        )

        if args.json:
            output = json.dumps(results, indent=2, ensure_ascii=False)
        elif args.bounding_boxes:
            lines = []
            for filename, data in results.items():
                lines.append(f"=== {filename} ===")
                if isinstance(data, list):
                    lines.append(format_bounding_boxes_text(data))
                else:
                    lines.append(data)
                lines.append("")
            output = '\n'.join(lines)
        else:
            lines = []
            for filename, text in results.items():
                lines.append(f"=== {filename} ===")
                lines.append(text)
                lines.append("")
            output = '\n'.join(lines)

        if args.output and not args.bounding_boxes:
            # Already saved individual files
            pass

        print(output)
        print(f"\nProcessed {len(results)} files")

    else:
        if args.pdf or (args.input and args.input.lower().endswith('.pdf')):
            # PDF mode: extract text from all pages
            pages = extract_text_from_pdf(
                args.input,
                lang=args.language,
                preprocess=args.preprocess
            )
            if args.json:
                output = json.dumps(pages, indent=2, ensure_ascii=False)
            else:
                output = '\n\n'.join(f"[Page {p['page']}]\n{p['text']}" for p in pages)

            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(output)
                print(f"PDF text ({len(pages)} pages) saved to {args.output}")
            else:
                print(output)
                print(f"\nExtracted text from {len(pages)} pages")
        else:
            text = extract_text(
                args.input,
                lang=args.language,
                preprocess=args.preprocess,
                bounding_boxes=args.bounding_boxes
            )

            if args.json:
                if args.bounding_boxes:
                    output = json.dumps(text, indent=2, ensure_ascii=False)
                else:
                    output = json.dumps({'text': text}, indent=2, ensure_ascii=False)
            elif args.bounding_boxes:
                output = format_bounding_boxes_text(text)
            else:
                output = text

            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(output if isinstance(output, str) else json.dumps(output))
                print(f"Text saved to {args.output}")
            else:
                print(output)


if __name__ == "__main__":
    main()