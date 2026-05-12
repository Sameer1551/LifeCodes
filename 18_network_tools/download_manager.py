#!/usr/bin/env python3
"""
Download Manager Tool
Multi-thread file downloader with progress tracking.
"""

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

import requests

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False


def get_filename_from_url(url: str, default: str = 'download') -> str:
    """Extract filename from URL."""
    parsed = urlparse(url)
    filename = os.path.basename(parsed.path)

    if not filename:
        filename = default

    return filename


def get_file_size(url: str) -> int | None:
    """Get file size from URL without downloading."""
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)
        return int(response.headers.get('Content-Length', 0))
    except:
        return None


def download_chunk(
    url: str,
    start: int,
    end: int,
    chunk_num: int,
    timeout: int = 30
) -> tuple[int, bytes]:
    """Download a specific byte range."""
    headers = {'Range': f'bytes={start}-{end}'}

    response = requests.get(url, headers=headers, timeout=30, stream=True)
    data = response.content

    return chunk_num, data


def download_file_multithread(
    url: str,
    output_path: str,
    threads: int = 4,
    chunk_size_mb: int = 1,
    timeout: int = 30,
    verbose: bool = True
) -> dict:
    """
    Download a file using multiple threads.

    Args:
        url: Download URL.
        output_path: Output file path.
        threads: Number of threads.
        chunk_size_mb: Chunk size in MB.
        timeout: Request timeout.
        verbose: Show progress.

    Returns:
        Dictionary with download info.
    """
    result = {
        'url': url,
        'output': output_path,
        'size_bytes': 0,
        'download_time_s': 0,
        'speed_mbps': 0,
        'success': False,
        'error': None
    }

    start_time = time.time()

    try:
        # Get file size
        file_size = get_file_size(url)

        if file_size is None or file_size == 0:
            # Fall back to single-threaded download
            return download_file_single(url, output_path, timeout, verbose)

        chunk_size = chunk_size_mb * 1024 * 1024
        num_chunks = (file_size + chunk_size - 1) // chunk_size

        # Create output directory
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Download chunks
        chunks = {}

        if verbose and HAS_TQDM:
            pbar = tqdm(total=file_size, unit='B', unit_scale=True, desc='Downloading')
        else:
            pbar = None

        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {}

            for i in range(num_chunks):
                start_byte = i * chunk_size
                end_byte = min(start_byte + chunk_size - 1, file_size - 1)

                future = executor.submit(
                    download_chunk, url, start_byte, end_byte, i, timeout
                )
                futures[future] = i

            for future in as_completed(futures):
                chunk_num, data = future.result()
                chunks[chunk_num] = data

                if pbar:
                    pbar.update(len(data))

        if pbar:
            pbar.close()

        # Write file
        with open(output_path, 'wb') as f:
            for i in range(num_chunks):
                if i in chunks:
                    f.write(chunks[i])

        end_time = time.time()
        download_time = end_time - start_time

        result['size_bytes'] = file_size
        result['download_time_s'] = round(download_time, 2)
        result['speed_mbps'] = round(file_size / download_time / 1024 / 1024, 2)
        result['success'] = True

    except Exception as e:
        result['error'] = str(e)

    return result


def download_file_single(
    url: str,
    output_path: str,
    timeout: int = 30,
    verbose: bool = True
) -> dict:
    """
    Download a file using single thread.

    Args:
        url: Download URL.
        output_path: Output file path.
        timeout: Request timeout.
        verbose: Show progress.

    Returns:
        Dictionary with download info.
    """
    result = {
        'url': url,
        'output': output_path,
        'size_bytes': 0,
        'download_time_s': 0,
        'speed_mbps': 0,
        'success': False,
        'error': None
    }

    start_time = time.time()

    try:
        # Create output directory
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        response = requests.get(url, timeout=timeout, stream=True)
        response.raise_for_status()

        total_size = int(response.headers.get('Content-Length', 0))

        if verbose and HAS_TQDM and total_size > 0:
            pbar = tqdm(total=total_size, unit='B', unit_scale=True, desc='Downloading')
        else:
            pbar = None

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                if pbar:
                    pbar.update(len(chunk))

        if pbar:
            pbar.close()

        end_time = time.time()
        download_time = end_time - start_time

        result['size_bytes'] = os.path.getsize(output_path)
        result['download_time_s'] = round(download_time, 2)
        result['speed_mbps'] = round(result['size_bytes'] / download_time / 1024 / 1024, 2)
        result['success'] = True

    except Exception as e:
        result['error'] = str(e)

    return result


def download_files_batch(
    urls: list[str],
    output_dir: str,
    threads: int = 4,
    verbose: bool = True
) -> list[dict]:
    """
    Download multiple files.

    Args:
        urls: List of URLs to download.
        output_dir: Output directory.
        threads: Threads per file.
        verbose: Show progress.

    Returns:
        List of download results.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    results = []

    for i, url in enumerate(urls, 1):
        filename = get_filename_from_url(url)
        output_path = os.path.join(output_dir, filename)

        if verbose:
            print(f"\n[{i}/{len(urls)}] Downloading: {url}")

        result = download_file_multithread(
            url, output_path, threads=threads, verbose=verbose
        )
        results.append(result)

        if verbose:
            if result['success']:
                print(f"  Done: {result['size_bytes']} bytes in {result['download_time_s']}s")
            else:
                print(f"  Error: {result['error']}")

    return results


def format_size(size_bytes: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"


def main():
    parser = argparse.ArgumentParser(
        description="Multi-thread file downloader."
    )
    parser.add_argument(
        "-u", "--url",
        type=str,
        help="URL to download"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Output file path"
    )
    parser.add_argument(
        "-f", "--file",
        type=str,
        help="File with URLs to download (one per line)"
    )
    parser.add_argument(
        "-d", "--directory",
        type=str,
        help="Output directory for batch downloads"
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=4,
        help="Number of threads per file (default: 4)"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1,
        help="Chunk size in MB (default: 1)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show download progress"
    )

    args = parser.parse_args()

    if not args.url and not args.file:
        parser.error("Either --url or --file is required")

    # Batch download
    if args.file:
        output_dir = args.directory or 'downloads'

        with open(args.file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]

        results = download_files_batch(urls, output_dir, args.threads, args.verbose)

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"\nDownload Summary:")
            print("=" * 50)

            total_size = 0
            successful = 0

            for r in results:
                if r['success']:
                    successful += 1
                    total_size += r['size_bytes']
                    print(f"✓ {r['output']}: {format_size(r['size_bytes'])}")
                else:
                    print(f"✗ {r['url']}: {r['error']}")

            print(f"\n{successful}/{len(results)} files downloaded")
            print(f"Total: {format_size(total_size)}")

    # Single file download
    else:
        if not args.output:
            args.output = get_filename_from_url(args.url)

        if args.verbose:
            print(f"Downloading: {args.url}")
            print(f"Output: {args.output}")
            print(f"Threads: {args.threads}")

        result = download_file_multithread(
            args.url,
            args.output,
            threads=args.threads,
            chunk_size_mb=args.chunk_size,
            timeout=args.timeout,
            verbose=args.verbose
        )

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result['success']:
                print(f"\nDownloaded: {format_size(result['size_bytes'])}")
                print(f"Time: {result['download_time_s']}s")
                print(f"Speed: {result['speed_mbps']} MB/s")
                print(f"Saved to: {args.output}")
            else:
                print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()