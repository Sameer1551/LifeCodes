#!/usr/bin/env python3
"""
Language Detector Tool
Detect the source language of a given text.
"""

import argparse
from langdetect import detect, detect_langs, LangDetectException


def detect_language(text: str) -> str:
    """
    Detect the primary language of text.

    Args:
        text: Input text to analyze.

    Returns:
        ISO language code (e.g., "en", "es").
    """
    try:
        return detect(text)
    except LangDetectException:
        return "unknown"


def detect_language_with_probabilities(text: str) -> list[tuple[str, float]]:
    """
    Detect language with probability scores.

    Args:
        text: Input text to analyze.

    Returns:
        List of (language_code, probability) tuples.
    """
    try:
        results = detect_langs(text)
        return [(lang.lang, lang.prob) for lang in results]
    except LangDetectException:
        return [("unknown", 0.0)]


LANGUAGE_NAMES = {
    "en": "English", "es": "Spanish", "fr": "French", "de": "German",
    "it": "Italian", "pt": "Portuguese", "ru": "Russian", "ja": "Japanese",
    "ko": "Korean", "zh-cn": "Chinese (Simplified)", "zh-tw": "Chinese (Traditional)",
    "ar": "Arabic", "hi": "Hindi", "nl": "Dutch", "pl": "Polish",
    "tr": "Turkish", "vi": "Vietnamese", "th": "Thai", "id": "Indonesian",
    "uk": "Ukrainian", "cs": "Czech", "sv": "Swedish", "da": "Danish",
    "fi": "Finnish", "no": "Norwegian", "el": "Greek", "he": "Hebrew",
    "ro": "Romanian", "hu": "Hungarian", "bn": "Bengali", "ta": "Tamil",
}


def main():
    parser = argparse.ArgumentParser(
        description="Detect the language of text."
    )
    parser.add_argument(
        "-i", "--input",
        type=str,
        help="Input text to analyze"
    )
    parser.add_argument(
        "-f", "--file",
        type=str,
        help="Input file path"
    )
    parser.add_argument(
        "-p", "--probabilities",
        action="store_true",
        help="Show probability scores for all detected languages"
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

    if args.probabilities:
        results = detect_language_with_probabilities(text)
        output_lines = []
        for lang, prob in results:
            name = LANGUAGE_NAMES.get(lang, lang)
            output_lines.append(f"{lang:<6} ({name:<20}) - {prob*100:.1f}%")
        result = "\n".join(output_lines)
    else:
        lang = detect_language(text)
        name = LANGUAGE_NAMES.get(lang, lang)
        result = f"Detected language: {lang} ({name})"

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"Result written to {args.output}")
    else:
        print(result)


if __name__ == "__main__":
    main()