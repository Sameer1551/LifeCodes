#!/usr/bin/env python3
"""
Text Summarizer Tool
Summarize a text block down to a specific sentence count using extractive summarization.
"""

import argparse
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer


def summarize_text(text: str, sentence_count: int = 3, language: str = "english") -> list[str]:
    """
    Summarize text to a specific number of sentences.

    Args:
        text: The input text to summarize.
        sentence_count: Number of sentences to include in summary.
        language: Language for tokenization (default: english).

    Returns:
        List of summary sentences.
    """
    parser = PlaintextParser.from_string(text, Tokenizer(language))
    summarizer = LexRankSummarizer()

    summary = summarizer(parser.document, sentence_count)
    return [str(sentence) for sentence in summary]


def main():
    parser = argparse.ArgumentParser(
        description="Summarize text to a specific sentence count."
    )
    parser.add_argument(
        "-i", "--input",
        type=str,
        help="Input text to summarize"
    )
    parser.add_argument(
        "-f", "--file",
        type=str,
        help="Input file path"
    )
    parser.add_argument(
        "-n", "--sentences",
        type=int,
        default=3,
        help="Number of sentences in summary (default: 3)"
    )
    parser.add_argument(
        "-l", "--language",
        type=str,
        default="english",
        help="Language for tokenization (default: english)"
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

    summary = summarize_text(text, args.sentences, args.language)

    result = "\n".join(f"- {sentence}" for sentence in summary)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"Summary written to {args.output}")
    else:
        print("\nSummary:")
        print(result)


if __name__ == "__main__":
    main()