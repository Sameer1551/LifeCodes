import os
import argparse
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from tqdm import tqdm

# -----------------------------
# Dependency check
# -----------------------------
missing = []

try:
    import pandas as pd
except ImportError:
    missing.append("pandas")

try:
    import fitz
except ImportError:
    missing.append("pymupdf")

try:
    from docx import Document
except ImportError:
    missing.append("python-docx")

if missing:
    print("Missing dependencies:")
    for m in missing:
        print("  pip install", m)
    exit()


# -----------------------------
# Extractor Registry
# -----------------------------
EXTRACTORS = {}

def register(ext):
    def wrapper(func):
        EXTRACTORS[ext] = func
        return func
    return wrapper


# -----------------------------
# File Extractors
# -----------------------------
@register(".txt")
def extract_txt(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


@register(".md")
def extract_md(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


@register(".pdf")
def extract_pdf(path):
    text = ""
    with fitz.open(path) as doc:
        for page in doc:
            text += page.get_text()
    return text


@register(".docx")
def extract_docx(path):
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


@register(".csv")
def extract_csv(path):
    df = pd.read_csv(path)
    return df.to_string()


@register(".xlsx")
def extract_xlsx(path):
    df = pd.read_excel(path)
    return df.to_string()


@register(".html")
def extract_html(path):
    from bs4 import BeautifulSoup

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f, "html.parser")
        return soup.get_text()


# -----------------------------
# Dispatcher
# -----------------------------
def extract_text(file_path):
    ext = Path(file_path).suffix.lower()

    extractor = EXTRACTORS.get(ext)

    if extractor:
        return extractor(file_path)

    return ""


# -----------------------------
# Safe extraction
# -----------------------------
def safe_extract(file):

    try:
        text = extract_text(file)

        if text is None:
            text = ""

        return file, text

    except Exception as e:
        return file, f"[ERROR] {str(e)}"


# -----------------------------
# File discovery
# -----------------------------
def collect_files(folder):

    skip_patterns = ["~$", ".DS_Store", "Thumbs.db"]

    files = []

    for root, _, filenames in os.walk(folder):

        for name in filenames:

            if any(p in name for p in skip_patterns):
                continue

            path = os.path.join(root, name)

            ext = Path(path).suffix.lower()

            if ext in EXTRACTORS:
                files.append(path)

    return files


# -----------------------------
# Main processing
# -----------------------------
def process_files(input_dir, output_file, workers):

    files = collect_files(input_dir)

    if not files:
        print("No supported files found.")
        return

    print(f"Found {len(files)} files")

    with open(output_file, "w", encoding="utf-8") as out:

        with ProcessPoolExecutor(max_workers=workers) as executor:

            results = executor.map(safe_extract, files)

            for file, text in tqdm(results, total=len(files)):

                out.write("\n")
                out.write("=" * 80 + "\n")
                out.write(file + "\n")
                out.write("=" * 80 + "\n")
                out.write(text + "\n")


# -----------------------------
# CLI
# -----------------------------
def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        required=True,
        help="Input folder containing files"
    )

    parser.add_argument(
        "--output",
        default="output.txt",
        help="Output text file"
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=os.cpu_count(),
        help="Number of parallel workers"
    )

    args = parser.parse_args()

    process_files(args.input, args.output, args.workers)


if __name__ == "__main__":
    main()