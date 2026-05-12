#!/usr/bin/env python3
"""
Text Normalizer Tool
Clean and standardize text for downstream processing.
"""

import argparse
import re
import string
import unicodedata


def normalize_text(
    text: str,
    lowercase: bool = True,
    remove_punctuation: bool = True,
    remove_numbers: bool = False,
    normalize_unicode: bool = True,
    collapse_whitespace: bool = True,
    remove_urls: bool = False,
    remove_emails: bool = False
) -> str:
    """
    Normalize text with various cleaning options.

    Args:
        text: Input text to normalize.
        lowercase: Convert to lowercase.
        remove_punctuation: Remove all punctuation marks.
        remove_numbers: Remove digits.
        normalize_unicode: Normalize unicode (NFKD).
        collapse_whitespace: Collapse multiple spaces to single space.
        remove_urls: Remove URLs from text.
        remove_emails: Remove email addresses from text.

    Returns:
        Normalized text.
    """
    result = text

    if normalize_unicode:
        result = unicodedata.normalize("NFKD", result)

    if remove_urls:
        result = re.sub(r"https?://\S+|www\.\S+", "", result)

    if remove_emails:
        result = re.sub(r"\S+@\S+\.\S+", "", result)

    if remove_numbers:
        result = re.sub(r"\d+", "", result)

    if remove_punctuation:
        result = result.translate(str.maketrans("", "", string.punctuation))

    if lowercase:
        result = result.lower()

    if collapse_whitespace:
        result = re.sub(r"\s+", " ", result).strip()

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Normalize and clean text."
    )
    parser.add_argument(
        "-i", "--input",
        type=str,
        help="Input text to normalize"
    )
    parser.add_argument(
        "-f", "--file",
        type=str,
        help="Input file path"
    )
    parser.add_argument(
        "--no-lowercase",
        action="store_true",
        help="Keep original case"
    )
    parser.add_argument(
        "--keep-punctuation",
        action="store_true",
        help="Keep punctuation"
    )
    parser.add_argument(
        "--remove-numbers",
        action="store_true",
        help="Remove digits from text"
    )
    parser.add_argument(
        "--keep-unicode",
        action="store_true",
        help="Skip unicode normalization"
    )
    parser.add_argument(
        "--remove-urls",
        action="store_true",
        help="Remove URLs from text"
    )
    parser.add_argument(
        "--remove-emails",
        action="store_true",
        help="Remove email addresses from text"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Output file path (optional)"
    )

    args = parser.parse_args()

    if not args.input and not args.file:
        parser.error("Either --input or --file is required")

    text = args.input if args.input else open(args.file, "r", encoding="utf-8").read()

    normalized = normalize_text(
        text,
        lowercase=not args.no_lowercase,
        remove_punctuation=not args.keep_punctuation,
        remove_numbers=args.remove_numbers,
        normalize_unicode=not args.keep_unicode,
        remove_urls=args.remove_urls,
        remove_emails=args.remove_emails
    )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(normalized)
        print(f"Normalized text written to {args.output}")
    else:
        print("Normalized text:")
        print("-" * 40)
        print(normalized)


if __name__ == "__main__":
    main()