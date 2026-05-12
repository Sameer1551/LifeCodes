#!/usr/bin/env python3
"""
Word Frequency Counter Tool
Identify the most common terms in text.
"""

import argparse
import re
from collections import Counter
from typing import Optional


def get_stopwords(language: str = "english") -> set[str]:
    """Get stopwords for filtering."""
    try:
        import nltk
        nltk.data.find("corpora/stopwords")
    except LookupError:
        import nltk
        nltk.download("stopwords", quiet=True)

    from nltk.corpus import stopwords
    return set(stopwords.words(language))


def tokenize(text: str, lowercase: bool = True) -> list[str]:
    """
    Tokenize text into words.

    Args:
        text: Input text.
        lowercase: Convert to lowercase before tokenizing.

    Returns:
        List of words.
    """
    if lowercase:
        text = text.lower()
    words = re.findall(r"\b\w+\b", text)
    return words


def count_words(
    text: str,
    top_n: int = 10,
    remove_stopwords: bool = True,
    language: str = "english",
    min_length: int = 1,
    lowercase: bool = True
) -> list[tuple[str, int]]:
    """
    Count word frequencies in text.

    Args:
        text: Input text.
        top_n: Number of top results to return.
        remove_stopwords: Whether to filter stopwords.
        language: Language for stopwords.
        min_length: Minimum word length to include.
        lowercase: Convert to lowercase.

    Returns:
        List of (word, count) tuples sorted by frequency.
    """
    words = tokenize(text, lowercase)

    if remove_stopwords:
        stopwords = get_stopwords(language)
        words = [w for w in words if w.lower() not in stopwords]

    if min_length > 1:
        words = [w for w in words if len(w) >= min_length]

    counter = Counter(words)
    return counter.most_common(top_n)


def count_words_advanced(
    text: str,
    top_n: int = 10,
    remove_stopwords: bool = True,
    language: str = "english",
    min_length: int = 1,
    lowercase: bool = True,
    include_percentages: bool = True
) -> list[dict]:
    """
    Count word frequencies with additional statistics.

    Args:
        text: Input text.
        top_n: Number of top results to return.
        remove_stopwords: Whether to filter stopwords.
        language: Language for stopwords.
        min_length: Minimum word length.
        lowercase: Convert to lowercase.
        include_percentages: Include percentage in results.

    Returns:
        List of dicts with word, count, and percentage.
    """
    words = tokenize(text, lowercase)

    total_words = len(words)

    if remove_stopwords:
        stopwords = get_stopwords(language)
        words = [w for w in words if w.lower() not in stopwords]

    if min_length > 1:
        words = [w for w in words if len(w) >= min_length]

    counter = Counter(words)
    top_words = counter.most_common(top_n)

    if include_percentages:
        total_after_filter = len(words)
        results = []
        for word, count in top_words:
            percentage = (count / total_after_filter * 100) if total_after_filter > 0 else 0
            results.append({
                "word": word,
                "count": count,
                "percentage": round(percentage, 2)
            })
        return results

    return [{"word": w, "count": c} for w, c in top_words]


def format_output(results: list, format_type: str = "table") -> str:
    """Format word frequency results."""
    if format_type == "table":
        lines = ["Word          | Count | Percentage"]
        lines.append("-" * 36)
        for item in results:
            word = item["word"][:12].ljust(12)
            count = str(item["count"]).ljust(6)
            pct = f"{item['percentage']:.1f}%"
            lines.append(f"{word} | {count} | {pct}")
        return "\n".join(lines)

    elif format_type == "json":
        import json
        return json.dumps(results, indent=2)

    elif format_type == "csv":
        lines = ["word,count,percentage"]
        for item in results:
            lines.append(f"{item['word']},{item['count']},{item['percentage']}")
        return "\n".join(lines)

    elif format_type == "simple":
        return "\n".join(f"{item['word']}: {item['count']}" for item in results)

    return str(results)


def main():
    parser = argparse.ArgumentParser(
        description="Count word frequencies in text."
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
        "-n", "--top",
        type=int,
        default=10,
        help="Number of top words to show (default: 10)"
    )
    parser.add_argument(
        "--include-stopwords",
        action="store_true",
        help="Include stopwords in count"
    )
    parser.add_argument(
        "-l", "--language",
        type=str,
        default="english",
        help="Language for stopwords (default: english)"
    )
    parser.add_argument(
        "--min-length",
        type=int,
        default=1,
        help="Minimum word length (default: 1)"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["table", "json", "csv", "simple"],
        default="table",
        help="Output format (default: table)"
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

    results = count_words_advanced(
        text,
        top_n=args.top,
        remove_stopwords=not args.include_stopwords,
        language=args.language,
        min_length=args.min_length
    )

    output = format_output(results, args.format)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Word frequencies written to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()