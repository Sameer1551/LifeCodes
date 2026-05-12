#!/usr/bin/env python3
"""
Text Similarity Checker Tool
Measure how related two documents/strings are using cosine similarity.
"""

import argparse
from typing import Optional


def calculate_similarity(text1: str, text2: str) -> float:
    """
    Calculate cosine similarity between two texts using TF-IDF.

    Args:
        text1: First text.
        text2: Second text.

    Returns:
        Similarity score between 0 and 1.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([text1, text2])

    similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
    return float(similarity[0][0])


def calculate_similarity_with_details(text1: str, text2: str) -> dict:
    """
    Calculate similarity with detailed information.

    Args:
        text1: First text.
        text2: Second text.

    Returns:
        Dict with similarity score and common terms.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([text1, text2])

    similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])

    feature_names = vectorizer.get_feature_names_out()

    tfidf1 = tfidf_matrix[0].toarray().flatten()
    tfidf2 = tfidf_matrix[1].toarray().flatten()

    top_indices1 = tfidf1.argsort()[-5:][::-1]
    top_indices2 = tfidf2.argsort()[-5:][::-1]

    top_terms1 = [(feature_names[i], round(tfidf1[i], 4)) for i in top_indices1 if tfidf1[i] > 0]
    top_terms2 = [(feature_names[i], round(tfidf2[i], 4)) for i in top_indices2 if tfidf2[i] > 0]

    return {
        "similarity": round(float(similarity[0][0]), 4),
        "similarity_percent": round(float(similarity[0][0]) * 100, 2),
        "top_terms_text1": top_terms1,
        "top_terms_text2": top_terms2
    }


def compare_files(file1: str, file2: str) -> dict:
    """
    Compare two files for similarity.

    Args:
        file1: Path to first file.
        file2: Path to second file.

    Returns:
        Similarity details.
    """
    with open(file1, "r", encoding="utf-8") as f:
        text1 = f.read()

    with open(file2, "r", encoding="utf-8") as f:
        text2 = f.read()

    return calculate_similarity_with_details(text1, text2)


def format_result(result: dict, format_type: str = "text") -> str:
    """Format similarity result."""
    if format_type == "json":
        import json
        return json.dumps(result, indent=2)

    lines = [
        f"Similarity Score: {result['similarity_percent']}%",
        f"  (Raw: {result['similarity']})",
        "",
        "Top terms in Text 1:",
    ]
    for term, score in result["top_terms_text1"]:
        lines.append(f"  - {term}: {score}")

    lines.append("")
    lines.append("Top terms in Text 2:")
    for term, score in result["top_terms_text2"]:
        lines.append(f"  - {term}: {score}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Compare similarity between two texts."
    )
    parser.add_argument(
        "-t1", "--text1",
        type=str,
        help="First text to compare"
    )
    parser.add_argument(
        "-t2", "--text2",
        type=str,
        help="Second text to compare"
    )
    parser.add_argument(
        "-f1", "--file1",
        type=str,
        help="First file to compare"
    )
    parser.add_argument(
        "-f2", "--file2",
        type=str,
        help="Second file to compare"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Output file path (optional)"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Only output the similarity percentage"
    )

    args = parser.parse_args()

    if args.text1 and args.text2:
        text1, text2 = args.text1, args.text2
    elif args.file1 and args.file2:
        with open(args.file1, "r", encoding="utf-8") as f:
            text1 = f.read()
        with open(args.file2, "r", encoding="utf-8") as f:
            text2 = f.read()
    else:
        parser.error("Provide either --text1 and --text2, or --file1 and --file2")

    result = calculate_similarity_with_details(text1, text2)

    if args.quiet:
        output = f"{result['similarity_percent']:.2f}%"
    else:
        output = format_result(result, args.format)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Result written to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()