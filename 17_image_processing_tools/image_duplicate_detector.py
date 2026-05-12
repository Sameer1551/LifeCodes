#!/usr/bin/env python3
"""
Image Duplicate Detector Tool
Find duplicate or near-duplicate images using perceptual hashing.
"""

import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image

try:
    import imagehash
    HAS_IMAGEHASH = True
except ImportError:
    HAS_IMAGEHASH = False


SUPPORTED_FORMATS = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tiff')

def _get_hash_methods() -> dict:
    """Build hash method map lazily — only when imagehash is confirmed available."""
    if not HAS_IMAGEHASH:
        return {}
    return {
        'phash': imagehash.phash,
        'dhash': imagehash.dhash,
        'ahash': imagehash.average_hash,
        'whash': imagehash.whash,
    }


def compute_file_hash(image_path: str) -> str:
    """Compute MD5 hash of file content for exact duplicate detection."""
    with open(image_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def compute_perceptual_hash(image_path: str, method: str = 'phash') -> str:
    """
    Compute perceptual hash of image.

    Args:
        image_path: Path to image file.
        method: Hash method (phash/dhash/ahash/whash).

    Returns:
        Hash string.
    """
    img = Image.open(image_path)

    hash_methods = _get_hash_methods()
    if method not in hash_methods:
        method = 'phash'

    hash_func = hash_methods[method]
    return str(hash_func(img))


def find_exact_duplicates(directory: str) -> dict[str, list[str]]:
    """
    Find exact duplicates using file hash.

    Args:
        directory: Path to directory to search.

    Returns:
        Dictionary mapping hash to list of file paths.
    """
    dir_path = Path(directory)
    image_files = [f for f in dir_path.iterdir() if f.suffix.lower() in SUPPORTED_FORMATS]

    hash_map: dict[str, list[str]] = {}

    for img_file in image_files:
        try:
            file_hash = compute_file_hash(str(img_file))
            if file_hash not in hash_map:
                hash_map[file_hash] = []
            hash_map[file_hash].append(str(img_file))
        except Exception as e:
            print(f"Error hashing {img_file.name}: {e}")

    # Return only duplicates
    return {h: paths for h, paths in hash_map.items() if len(paths) > 1}


def find_similar_images(
    directory: str,
    threshold: int = 8,
    method: str = 'phash'
) -> list[tuple[str, str, int]]:
    """
    Find similar images using perceptual hashing.

    Args:
        directory: Path to directory to search.
        threshold: Maximum hamming distance to consider as similar.
        method: Hash method (phash/dhash/ahash/whash).

    Returns:
        List of tuples (path1, path2, distance).
    """
    if not HAS_IMAGEHASH:
        raise ImportError("imagehash library is required for similar image detection. Install with: pip install imagehash")

    dir_path = Path(directory)
    image_files = [f for f in dir_path.iterdir() if f.suffix.lower() in SUPPORTED_FORMATS]

    # Compute hashes for all images
    hash_map: dict[str, str] = {}
    for img_file in image_files:
        try:
            img_hash = compute_perceptual_hash(str(img_file), method)
            hash_map[str(img_file)] = img_hash
        except Exception as e:
            print(f"Error hashing {img_file.name}: {e}")

    # Compare all pairs
    similar_pairs: list[tuple[str, str, int]] = []
    paths = list(hash_map.keys())

    for i in range(len(paths)):
        for j in range(i + 1, len(paths)):
            path1, path2 = paths[i], paths[j]
            hash1 = imagehash.hex_to_hash(hash_map[path1])
            hash2 = imagehash.hex_to_hash(hash_map[path2])
            distance = hash1 - hash2

            if distance <= threshold:
                similar_pairs.append((path1, path2, distance))

    return similar_pairs


def format_results_human(
    exact_duplicates: dict[str, list[str]] | None,
    similar_pairs: list[tuple[str, str, int]] | None
) -> str:
    """Format results as human-readable text."""
    lines = []

    if exact_duplicates:
        lines.append("=== Exact Duplicates ===")
        if exact_duplicates:
            for file_hash, paths in exact_duplicates.items():
                lines.append(f"\nHash: {file_hash}")
                for path in paths:
                    lines.append(f"  - {path}")
        else:
            lines.append("No exact duplicates found.")

    if similar_pairs is not None:
        lines.append("\n=== Similar Images ===")
        if similar_pairs:
            for path1, path2, distance in similar_pairs:
                lines.append(f"\nDistance: {distance}")
                lines.append(f"  - {path1}")
                lines.append(f"  - {path2}")
        else:
            lines.append("No similar images found.")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Find duplicate or similar images using perceptual hashing."
    )
    parser.add_argument(
        "-d", "--directory",
        type=str,
        required=True,
        help="Directory to search for duplicates"
    )
    parser.add_argument(
        "-t", "--threshold",
        type=int,
        default=8,
        help="Maximum hamming distance for similarity (default: 8, lower = more similar)"
    )
    parser.add_argument(
        "-m", "--method",
        type=str,
        choices=['phash', 'dhash', 'ahash', 'whash'],
        default='phash',
        help="Hash method (default: phash)"
    )
    parser.add_argument(
        "--exact",
        action="store_true",
        help="Find exact duplicates using MD5 hash"
    )
    parser.add_argument(
        "--similar",
        action="store_true",
        help="Find similar images using perceptual hash"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Output file for results (JSON format)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print progress information"
    )

    args = parser.parse_args()

    # Default to both exact and similar if neither specified
    if not args.exact and not args.similar:
        args.exact = True
        args.similar = True

    exact_duplicates = None
    similar_pairs = None

    if args.exact:
        if args.verbose:
            print("Finding exact duplicates...")
        exact_duplicates = find_exact_duplicates(args.directory)
        if args.verbose:
            print(f"Found {len(exact_duplicates)} groups of exact duplicates")

    if args.similar:
        if args.verbose:
            print("Finding similar images...")
        try:
            similar_pairs = find_similar_images(
                args.directory,
                threshold=args.threshold,
                method=args.method
            )
            if args.verbose:
                print(f"Found {len(similar_pairs)} pairs of similar images")
        except ImportError as e:
            print(f"Error: {e}")
            similar_pairs = []

    # Output results
    if args.output:
        results = {}
        if exact_duplicates is not None:
            results['exact_duplicates'] = exact_duplicates
        if similar_pairs is not None:
            results['similar_images'] = [
                {'path1': p1, 'path2': p2, 'distance': d}
                for p1, p2, d in similar_pairs
            ]
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        print(f"Results written to {args.output}")
    else:
        print(format_results_human(exact_duplicates, similar_pairs))


if __name__ == "__main__":
    main()