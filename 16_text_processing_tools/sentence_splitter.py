#!/usr/bin/env python3
"""
Sentence Splitter Tool
Divide text into discrete, analyzeable sentences.
"""

import argparse
from typing import Optional


def download_nltk_data():
    """Download required NLTK data if not present."""
    import nltk
    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        nltk.download("punkt", quiet=True)
    try:
        nltk.data.find("tokenizers/punkt_tab")
    except LookupError:
        nltk.download("punkt_tab", quiet=True)


def split_sentences(text: str, language: str = "english") -> list[str]:
    """
    Split text into sentences using NLTK's sent_tokenize.

    Args:
        text: Input text to split.
        language: Language for tokenization.

    Returns:
        List of sentences.
    """
    download_nltk_data()

    from nltk.tokenize import sent_tokenize
    return sent_tokenize(text, language=language)


def split_sentences_with_indices(text: str, language: str = "english") -> list[tuple[str, int, int]]:
    """
    Split text into sentences with their start and end indices.

    Args:
        text: Input text to split.
        language: Language for tokenization.

    Returns:
        List of (sentence, start_index, end_index) tuples.
    """
    download_nltk_data()

    from nltk.tokenize import sent_tokenize
    sentences = sent_tokenize(text, language=language)

    result = []
    current_pos = 0
    for sentence in sentences:
        start = text.find(sentence, current_pos)
        if start == -1:
            start = current_pos
        end = start + len(sentence)
        result.append((sentence, start, end))
        current_pos = end

    return result


def split_file(
    input_path: str,
    output_path: Optional[str] = None,
    language: str = "english",
    format_type: str = "list"
) -> list[str]:
    """
    Split a file into sentences.

    Args:
        input_path: Path to input file.
        output_path: Path to output file (optional).
        language: Language for tokenization.
        format_type: Output format ('list', 'numbered', 'json').

    Returns:
        List of sentences.
    """
    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()

    sentences = split_sentences(text, language)

    if output_path:
        output_content = ""
        if format_type == "list":
            output_content = "\n".join(f"- {s}" for s in sentences)
        elif format_type == "numbered":
            output_content = "\n".join(f"{i+1}. {s}" for i, s in enumerate(sentences))
        elif format_type == "json":
            import json
            output_content = json.dumps(sentences, indent=2, ensure_ascii=False)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output_content)

    return sentences


SUPPORTED_LANGUAGES = [
    "czech", "danish", "dutch", "english", "estonian",
    "finnish", "french", "german", "greek", "italian",
    "norwegian", "polish", "portuguese", "slovene", "spanish",
    "swedish", "turkish"
]


def main():
    parser = argparse.ArgumentParser(
        description="Split text into sentences."
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
        choices=SUPPORTED_LANGUAGES,
        help="Language for tokenization (default: english)"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["list", "numbered", "json"],
        default="list",
        help="Output format (default: list)"
    )
    parser.add_argument(
        "--list-languages",
        action="store_true",
        help="List supported languages and exit"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Output file path (optional)"
    )

    args = parser.parse_args()

    if args.list_languages:
        print("Supported languages:")
        for lang in SUPPORTED_LANGUAGES:
            print(f"  - {lang}")
        return

    if not args.input and not args.file:
        parser.error("Either --input or --file is required")

    text = args.input if args.input else open(args.file, "r", encoding="utf-8").read()

    sentences = split_sentences(text, args.language)

    if args.format == "list":
        output = "\n".join(f"- {s}" for s in sentences)
    elif args.format == "numbered":
        output = "\n".join(f"{i+1}. {s}" for i, s in enumerate(sentences))
    elif args.format == "json":
        import json
        output = json.dumps(sentences, indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Sentences written to {args.output}")
    else:
        print(f"Found {len(sentences)} sentences:\n")
        print(output)


if __name__ == "__main__":
    main()