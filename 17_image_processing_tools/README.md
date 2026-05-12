# Image Processing Tools

A collection of 12 command-line utilities for image processing tasks including resizing, format conversion, metadata extraction, watermarking, compression, duplicate detection, OCR, background removal, screenshots, dataset organization, and privacy-focused metadata viewing and removal.

## Installation

```bash
pip install -r requirements.txt
```

### External Dependencies

Some tools require additional system software:

- **OCR Tool**: [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) must be installed separately
- **PDF OCR**: [Poppler](https://github.com/oschwartz10612/poppler-windows/releases) (Windows) or `poppler-utils` (Linux) or `brew install poppler` (macOS)
- **Web Screenshots**: Run `playwright install` after installing dependencies

## Tools

### 1. image_resizer.py

Resize images by dimensions or percentage with aspect ratio preservation.

```bash
# Resize by width (aspect ratio preserved)
python image_resizer.py -i input.jpg -o output.jpg --width 800

# Resize by height
python image_resizer.py -i input.jpg -o output.jpg --height 600

# Resize by scale (50%)
python image_resizer.py -i input.jpg -o output.jpg --scale 0.5

# Resize entire directory
python image_resizer.py -d images/ -o resized/ --width 800

# Disable aspect ratio preservation
python image_resizer.py -i input.jpg -o output.jpg --width 800 --height 600 --no-aspect

# Convert format while resizing
python image_resizer.py -i input.png -o output.jpg --width 800 -f jpg
```

**Options:**
- `-i/--input`: Input image file
- `-d/--directory`: Input directory (batch mode)
- `-o/--output`: Output file or directory
- `--width`: Target width in pixels
- `--height`: Target height in pixels
- `--scale`: Scale factor (0.5 = 50%, 2.0 = 200%)
- `--no-aspect`: Disable aspect ratio preservation
- `-f/--format`: Output format (png/jpg/webp/bmp/gif/tiff)
- `-v/--verbose`: Print progress information

---

### 2. image_format_converter.py

Convert images between formats (PNG, JPG, WEBP, BMP, GIF, TIFF).

```bash
# Convert single file
python image_format_converter.py -i input.png -o output.jpg

# Convert with quality setting
python image_format_converter.py -i input.png -o output.jpg -q 90

# Batch convert directory
python image_format_converter.py -d images/ -o converted/ -f webp

# Strip metadata during conversion
python image_format_converter.py -i input.jpg -o output.jpg --strip-metadata
```

**Options:**
- `-i/--input`: Input image file
- `-d/--directory`: Input directory (batch mode)
- `-o/--output`: Output file or directory
- `-f/--format`: Output format (required for batch mode)
- `-q/--quality`: Quality 1-100 for lossy formats (default: 85)
- `--strip-metadata`: Remove EXIF metadata
- `-v/--verbose`: Print progress information

---

### 3. image_metadata_reader.py

Extract EXIF metadata from image files.

```bash
# Read metadata from single image
python image_metadata_reader.py -i photo.jpg

# Output as JSON
python image_metadata_reader.py -i photo.jpg --json

# Exclude GPS data
python image_metadata_reader.py -i photo.jpg --no-gps

# Batch process directory
python image_metadata_reader.py -d photos/ -o metadata.json --json

# Save to file
python image_metadata_reader.py -i photo.jpg -o metadata.txt
```

**Options:**
- `-i/--input`: Input image file
- `-d/--directory`: Input directory (batch mode)
- `--json`: Output in JSON format
- `--no-gps`: Exclude GPS data
- `--no-exifread`: Use Pillow only (no exifread)
- `-o/--output`: Output file path

---

### 4. image_watermarker.py

Add text or image watermarks to images.

```bash
# Add text watermark (centered)
python image_watermarker.py -i photo.jpg -o watermarked.jpg -t "© Your Name"

# Position watermark
python image_watermarker.py -i photo.jpg -o watermarked.jpg -t "© Your Name" -p bottomright

# Adjust opacity
python image_watermarker.py -i photo.jpg -o watermarked.jpg -t "© Your Name" --opacity 0.3

# Tile watermark across image
python image_watermarker.py -i photo.jpg -o watermarked.jpg -t "DRAFT" --tile

# Add image watermark (logo)
python image_watermarker.py -i photo.jpg -o watermarked.jpg -w logo.png -p bottomright --opacity 0.7

# Batch process directory
python image_watermarker.py -d photos/ -o watermarked/ -t "© Your Name"
```

**Options:**
- `-i/--input`: Input image file
- `-d/--directory`: Input directory (batch mode)
- `-o/--output`: Output file or directory
- `-t/--text`: Text watermark content
- `-w/--watermark`: Path to watermark image
- `-p/--position`: Position (center/topleft/topright/bottomleft/bottomright)
- `--opacity`: Opacity 0.0-1.0 (default: 0.5)
- `--font-size`: Font size for text (default: 36)
- `--font-color`: Font color hex/name (default: #FFFFFF)
- `--scale`: Scale factor for image watermark
- `--tile`: Tile watermark across image
- `-v/--verbose`: Print progress information

---

### 5. image_compressor.py

Reduce image file size while maintaining acceptable quality.

```bash
# Compress with quality setting
python image_compressor.py -i photo.jpg -o compressed.jpg -q 75

# Resize to max dimensions
python image_compressor.py -i photo.jpg -o compressed.jpg --max-width 1920 --max-height 1080

# Target specific file size
python image_compressor.py -i photo.jpg -o compressed.jpg --target-size 500000

# Batch compress directory
python image_compressor.py -d photos/ -o compressed/ -q 80 -v

# Disable PNG optimization
python image_compressor.py -i image.png -o compressed.png --no-optimize
```

**Options:**
- `-i/--input`: Input image file
- `-d/--directory`: Input directory (batch mode)
- `-o/--output`: Output file or directory
- `-q/--quality`: Quality 1-100 (default: 85)
- `--max-width`: Maximum width in pixels
- `--max-height`: Maximum height in pixels
- `--target-size`: Target file size in bytes (iterative compression)
- `--no-optimize`: Disable PNG optimization
- `-v/--verbose`: Print compression details

---

### 6. image_duplicate_detector.py

Find duplicate or near-duplicate images using perceptual hashing.

```bash
# Find all duplicates (exact and similar)
python image_duplicate_detector.py -d photos/

# Find exact duplicates only
python image_duplicate_detector.py -d photos/ --exact

# Find similar images only
python image_duplicate_detector.py -d photos/ --similar

# Adjust similarity threshold
python image_duplicate_detector.py -d photos/ -t 5 --similar

# Use different hash method
python image_duplicate_detector.py -d photos/ -m dhash --similar

# Save results to JSON
python image_duplicate_detector.py -d photos/ -o results.json
```

**Options:**
- `-d/--directory`: Directory to search (required)
- `-t/--threshold`: Hamming distance threshold (default: 8, lower = more similar)
- `-m/--method`: Hash method (phash/dhash/ahash/whash)
- `--exact`: Find exact duplicates using MD5 hash
- `--similar`: Find similar images using perceptual hash
- `-o/--output`: Output file for results (JSON)
- `-v/--verbose`: Print progress information

---

### 7. image_to_text_ocr.py

Extract text from images using OCR (Tesseract).

```bash
# Extract text from image
python image_to_text_ocr.py -i scan.jpg

# Specify language
python image_to_text_ocr.py -i scan.jpg -l fra

# Enable preprocessing for better results
python image_to_text_ocr.py -i scan.jpg --preprocess

# Get bounding boxes for each word
python image_to_text_ocr.py -i scan.jpg --bounding-boxes

# Batch process directory
python image_to_text_ocr.py -d scans/ -o texts/

# Extract from PDF
python image_to_text_ocr.py -i document.pdf --pdf

# Output as JSON
python image_to_text_ocr.py -i scan.jpg --json
```

**Options:**
- `-i/--input`: Input image file
- `-d/--directory`: Input directory (batch mode)
- `-o/--output`: Output file or directory
- `-l/--language`: Language code (eng/fra/deu/spa/chi_sim/jpn)
- `--preprocess`: Apply preprocessing (grayscale, threshold)
- `--bounding-boxes`: Output with bounding box coordinates
- `--json`: Output in JSON format
- `--pdf`: Treat input as PDF file
- `-v/--verbose`: Print progress information

---

### 8. image_background_remover.py

Remove backgrounds from images using AI (rembg).

```bash
# Remove background
python image_background_remover.py -i photo.jpg -o output.png

# Use faster model
python image_background_remover.py -i photo.jpg -o output.png -m u2netp

# Replace with custom background color
python image_background_remover.py -i photo.jpg -o output.png --background white
python image_background_remover.py -i photo.jpg -o output.png --background "#FF0000"

# Batch process directory
python image_background_remover.py -d photos/ -o nobg/ -v
```

**Options:**
- `-i/--input`: Input image file
- `-d/--directory`: Input directory (batch mode)
- `-o/--output`: Output file or directory
- `-m/--model`: AI model (u2net/u2netp/u2net_human_seg/isnet-general-use)
- `--background`: Background color (hex or name)
- `-v/--verbose`: Print progress information

**Note:** First run downloads the AI model automatically.

---

### 9. screenshot_capture.py

Take automated screenshots of desktop or websites.

```bash
# Capture primary monitor
python screenshot_capture.py --desktop -o screenshot.png

# Capture specific monitor
python screenshot_capture.py --desktop --monitor 2 -o monitor2.png

# Capture specific region
python screenshot_capture.py --desktop --region "0,0,800,600" -o region.png

# Capture all monitors
python screenshot_capture.py --desktop --monitor 0 -o all.png

# Capture website
python screenshot_capture.py --url "https://example.com" -o website.png

# Capture full page
python screenshot_capture.py --url "https://example.com" --full-page -o full.png

# Capture with delay for page load
python screenshot_capture.py --url "https://example.com" --delay 5 -o website.png

# Capture specific element
python screenshot_capture.py --url "https://example.com" --selector "#content" -o element.png

# Custom viewport size
python screenshot_capture.py --url "https://example.com" --viewport-width 1366 --viewport-height 768 -o mobile.png
```

**Desktop Options:**
- `--desktop`: Capture desktop screenshot
- `--monitor`: Monitor number (0=all, 1=primary)
- `--region`: Region as "left,top,width,height"

**Web Options:**
- `--url`: URL to capture
- `--full-page`: Capture entire page
- `--delay`: Wait time for page load (default: 2.0)
- `--viewport-width`: Browser width (default: 1920)
- `--viewport-height`: Browser height (default: 1080)
- `--selector`: CSS selector for specific element

**Common Options:**
- `-o/--output`: Output file path (required). Format is inferred from the extension (e.g. `output.png`, `output.jpg`)

---

### 10. image_dataset_organizer.py

Organize images into folders by date, size, dimensions, or color.

```bash
# Organize by date (year/month folders)
python image_dataset_organizer.py -i photos/ -o organized/ -b date

# Organize by file size
python image_dataset_organizer.py -i photos/ -o organized/ -b size

# Organize by orientation (portrait/landscape/square)
python image_dataset_organizer.py -i photos/ -o organized/ -b dimensions

# Organize by dominant color
python image_dataset_organizer.py -i photos/ -o organized/ -b color

# Move files instead of copying
python image_dataset_organizer.py -i photos/ -o organized/ --move

# Preview without making changes
python image_dataset_organizer.py -i photos/ -o organized/ --dry-run
```

**Options:**
- `-i/--input`: Input directory (required)
- `-o/--output`: Output directory (required)
- `-b/--by`: Organization criterion (date/size/dimensions/color)
- `--move`: Move files instead of copying
- `--dry-run`: Preview without making changes
- `-v/--verbose`: Print progress information

**Organization Categories:**
- **date**: `2024/01/`, `2024/02/`, etc.
- **size**: `small/` (<100KB), `medium/` (100KB-1MB), `large/` (1-10MB), `very_large/` (>10MB)
- **dimensions**: `portrait/`, `landscape/`, `square/`
- **color**: `red/`, `green/`, `blue/`, `white/`, `black/`, `yellow/`, etc.

---

### 11. image_info_viewer.py

View all metadata hidden inside an image — GPS location, device info, dates, author, and more. Highlights exactly what personal information is exposed.

```bash
# View all info from a single image
python image_info_viewer.py -i photo.jpg

# Quick privacy scan — show only what personal data is exposed
python image_info_viewer.py -i photo.jpg --privacy-check

# Scan an entire folder for privacy risks
python image_info_viewer.py -d photos/ --privacy-check

# Output as JSON
python image_info_viewer.py -i photo.jpg --json

# Save report to a file
python image_info_viewer.py -i photo.jpg -o report.txt
```

**Options:**
- `-i/--input`: Input image file to inspect
- `-d/--directory`: Directory of images (batch scan)
- `--privacy-check`: Show only the privacy risk summary
- `--json`: Output in JSON format
- `-o/--output`: Save output to a file

**Shows:**
- 📁 File info (format, dimensions, file size)
- 📷 Camera/device (make, model, lens, ISO, aperture, focal length)
- 📅 Dates (date taken, digitized, modified)
- 📍 GPS location with a direct Google Maps link
- 💻 Software/author fields (software, computer name, artist)
- 🔒 Privacy risk summary — highlights exactly what a stranger could learn from your image

---

### 12. image_metadata_remover.py

Strip **all** EXIF and embedded metadata from images to protect your personal information before sharing. Only the pixel data is kept.

**Removes:** GPS location, device make/model, date taken, software, author, copyright, and all other metadata fields.

```bash
# Clean a single image → save to a new file
python image_metadata_remover.py -i photo.jpg -o clean_photo.jpg

# Clean and overwrite the original (WARNING: original data is lost)
python image_metadata_remover.py -i photo.jpg --in-place

# Clean an entire folder
python image_metadata_remover.py -d photos/ -o cleaned/

# Clean entire folder in-place
python image_metadata_remover.py -d photos/ --in-place

# Clean and verify nothing remains
python image_metadata_remover.py -i photo.jpg -o clean.jpg --verify

# Verbose: see exactly what was stripped
python image_metadata_remover.py -i photo.jpg -o clean.jpg -v --verify
```

**Options:**
- `-i/--input`: Input image file
- `-d/--directory`: Input directory (batch mode)
- `-o/--output`: Output file or directory
- `--in-place`: Overwrite original file(s) directly
- `-q/--quality`: Output quality for JPEG/WEBP (default: 95)
- `--verify`: After cleaning, confirm no metadata remains
- `-v/--verbose`: Print which fields were stripped per file

> **Tip:** Use `image_info_viewer.py --privacy-check` before and after to confirm the metadata is gone.

---

## Supported Formats

| Tool        | PNG | JPG | WEBP  | BMP  | GIF | TIFF | PDF |
|-------------|-----|-----|-------|------|-----|------|-----|
| resizer     | ✓   | ✓   | ✓    | ✓   | ✓   | ✓    | -   |
| converter   | ✓   | ✓   | ✓    | ✓   | ✓   | ✓    | -   |
| metadata    | ✓   | ✓   | ✓    | ✓   | ✓   | ✓    | -   |
| watermarker | ✓   | ✓   | ✓    | ✓   | ✓   | ✓    | -   |
| compressor  | ✓   | ✓   | ✓    | -   | -   | ✓    | -   |
| duplicate   | ✓   | ✓   | ✓    | ✓   | ✓   | ✓    | -   |
| ocr         | ✓   | ✓   | ✓    | ✓   | ✓   | ✓    | ✓   |
| background  | ✓   | ✓   | ✓    | ✓   | -   | ✓    | -   |
| screenshot  | ✓   | ✓   | ✓    | ✓   | -   | -     | -   |
| organizer   | ✓   | ✓   | ✓    | ✓   | ✓   | ✓    | -   |
| info viewer | ✓   | ✓   | ✓    | ✓   | ✓   | ✓    | -   |
| meta remover| ✓   | ✓   | ✓    | ✓   | ✓   | ✓    | -   |

## Dependencies

```
Pillow>=10.0.0       # Core image processing
exifread>=3.0.0      # EXIF metadata extraction
imagehash>=4.3.1     # Perceptual hashing
pytesseract>=0.3.10  # OCR wrapper
pdf2image>=1.16.0    # PDF to image conversion
rembg>=2.0.50        # Background removal
mss>=9.0.0           # Desktop screenshots
playwright>=1.40.0   # Website screenshots
```

## License

MIT License