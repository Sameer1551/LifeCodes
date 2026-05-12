#!/usr/bin/env python3
"""
Keyword Extractor Tool
Identify key phrases and terms within a document using YAKE algorithm.
"""

import argparse
import yake


def extract_keywords(
    text: str,
    max_ngram_size: int = 2,
    num_keywords: int = 10,
    language: str = "en"
) -> list[tuple[str, float]]:
    """
    Extract keywords from text using YAKE algorithm.

    Args:
        text: The input text to analyze.
        max_ngram_size: Maximum n-gram size for keywords.
        num_keywords: Number of keywords to return.
        language: Language code (default: en).

    Returns:
        List of (keyword, score) tuples, lower score = more relevant.
    """
    kw_extractor = yake.KeywordExtractor(
        lan=language,
        n=max_ngram_size,
        top=num_keywords,
        dedupFunc="seqm"
    )
    keywords = kw_extractor.extract_keywords(text)
    return keywords


def main():
    parser = argparse.ArgumentParser(
        description="Extract keywords from text."
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
        "-n", "--num-keywords",
        type=int,
        default=10,
        help="Number of keywords to extract (default: 10)"
    )
    parser.add_argument(
        "-g", "--ngram",
        type=int,
        default=2,
        help="Maximum n-gram size (default: 2)"
    )
    parser.add_argument(
        "-l", "--language",
        type=str,
        default="en",
        help="Language code (default: en)"
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

    keywords = extract_keywords(text, args.ngram, args.num_keywords, args.language)

    result_lines = []
    for keyword, score in keywords:
        result_lines.append(f"{keyword:<30} (relevance: {1-score:.3f})")

    result = "\n".join(result_lines)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"Keywords written to {args.output}")
    else:
        print("\nExtracted Keywords:")
        print(result)


if __name__ == "__main__":
    main()