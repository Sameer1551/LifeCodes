#!/usr/bin/env python3
"""
Stopword Remover Tool
Strip "noise" words to focus on meaningful content.
"""

import argparse
from typing import Optional


def get_stopwords(language: str = "english") -> set[str]:
    """
    Get stopwords for a given language using NLTK.

    Args:
        language: Language name (e.g., "english", "spanish").

    Returns:
        Set of stopwords.
    """
    try:
        import nltk
        nltk.data.find("corpora/stopwords")
    except LookupError:
        import nltk
        nltk.download("stopwords", quiet=True)

    from nltk.corpus import stopwords
    return set(stopwords.words(language))


def remove_stopwords(
    text: str,
    language: str = "english",
    custom_stopwords: Optional[set[str]] = None
) -> str:
    """
    Remove stopwords from text.

    Args:
        text: Input text.
        language: Language for stopwords.
        custom_stopwords: Additional stopwords to remove.

    Returns:
        Text with stopwords removed.
    """
    stopwords = get_stopwords(language)

    if custom_stopwords:
        stopwords.update(custom_stopwords)

    words = text.split()
    filtered_words = [word for word in words if word.lower() not in stopwords]

    return " ".join(filtered_words)


def remove_stopwords_from_file(
    input_path: str,
    output_path: Optional[str] = None,
    language: str = "english"
) -> str:
    """
    Process a file and remove stopwords.

    Args:
        input_path: Path to input file.
        output_path: Path to output file (optional).
        language: Language for stopwords.

    Returns:
        Text with stopwords removed.
    """
    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()

    result = remove_stopwords(text, language)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result)

    return result


AVAILABLE_LANGUAGES = [
    "arabic", "azerbaijani", "bengali", "catalan", "chinese",
    "danish", "dutch", "english", "finnish", "french",
    "german", "greek", "hebrew", "hinglish", "hungarian",
    "indonesian", "italian", "kazakh", "nepali", "norwegian",
    "portuguese", "romanian", "russian", "slovak", "spanish",
    "swedish", "tajik", "turkish", "ukrainian", "vietnamese"
]


def main():
    parser = argparse.ArgumentParser(
        description="Remove stopwords from text."
    )
    parser.add_argument(
        "-i", "--input",
        type=str,
        help="Input text"
    )
    parser.add_argument(
        "-f", "--file",
        type=str,
        help="Input file path"
    )
    parser.add_argument(
        "-l", "--language",
        type=str,
        default="english",
        choices=AVAILABLE_LANGUAGES,
        help="Language for stopwords (default: english)"
    )
    parser.add_argument(
        "-c", "--custom-stopwords",
        type=str,
        help="Comma-separated additional stopwords to remove"
    )
    parser.add_argument(
        "--list-languages",
        action="store_true",
        help="List available languages and exit"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Output file path (optional)"
    )

    args = parser.parse_args()

    if args.list_languages:
        print("Available languages:")
        for lang in AVAILABLE_LANGUAGES:
            print(f"  - {lang}")
        return

    if not args.input and not args.file:
        parser.error("Either --input or --file is required")

    text = args.input if args.input else open(args.file, "r", encoding="utf-8").read()

    custom_sw = None
    if args.custom_stopwords:
        custom_sw = set(s.strip().lower() for s in args.custom_stopwords.split(","))

    result = remove_stopwords(text, args.language, custom_sw)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"Text with stopwords removed written to {args.output}")
    else:
        print("Text with stopwords removed:")
        print("-" * 40)
        print(result)


if __name__ == "__main__":
    main()