#!/usr/bin/env python3
"""
URL Metadata Fetcher Tool
Fetch title, description, and other metadata from URLs.
"""

import argparse
import json
import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


def fetch_metadata(url: str, timeout: int = 10) -> dict:
    """
    Fetch metadata from a URL.

    Args:
        url: URL to fetch metadata from.
        timeout: Request timeout in seconds.

    Returns:
        Dictionary with metadata.
    """
    # Ensure URL has scheme
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    result = {
        'url': url,
        'title': None,
        'description': None,
        'og_title': None,
        'og_description': None,
        'og_image': None,
        'og_type': None,
        'twitter_card': None,
        'twitter_title': None,
        'twitter_description': None,
        'twitter_image': None,
        'favicon': None,
        'canonical_url': None,
        'h1': None,
        'images': [],
        'error': None
    }

    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; MetadataFetcher/1.0)'
            }
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Title
        title_tag = soup.find('title')
        if title_tag:
            result['title'] = title_tag.get_text(strip=True)

        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            result['description'] = meta_desc.get('content')

        # Open Graph tags
        og_title = soup.find('meta', property='og:title')
        if og_title:
            result['og_title'] = og_title.get('content')

        og_desc = soup.find('meta', property='og:description')
        if og_desc:
            result['og_description'] = og_desc.get('content')

        og_image = soup.find('meta', property='og:image')
        if og_image:
            result['og_image'] = urljoin(url, og_image.get('content'))

        og_type = soup.find('meta', property='og:type')
        if og_type:
            result['og_type'] = og_type.get('content')

        # Twitter Card tags
        twitter_card = soup.find('meta', attrs={'name': 'twitter:card'})
        if twitter_card:
            result['twitter_card'] = twitter_card.get('content')

        twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
        if twitter_title:
            result['twitter_title'] = twitter_title.get('content')

        twitter_desc = soup.find('meta', attrs={'name': 'twitter:description'})
        if twitter_desc:
            result['twitter_description'] = twitter_desc.get('content')

        twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
        if twitter_image:
            result['twitter_image'] = urljoin(url, twitter_image.get('content'))

        # Favicon
        favicon = soup.find('link', rel='icon') or soup.find('link', rel='shortcut icon')
        if favicon:
            result['favicon'] = urljoin(url, favicon.get('href'))

        # Canonical URL
        canonical = soup.find('link', rel='canonical')
        if canonical:
            result['canonical_url'] = canonical.get('href')

        # H1 tag
        h1 = soup.find('h1')
        if h1:
            result['h1'] = h1.get_text(strip=True)

        # Find images (limit to 10)
        images = soup.find_all('img', limit=10)
        for img in images:
            src = img.get('src')
            if src:
                result['images'].append(urljoin(url, src))

    except requests.RequestException as e:
        result['error'] = str(e)
    except Exception as e:
        result['error'] = str(e)

    return result


def fetch_metadata_batch(
    urls: list[str],
    timeout: int = 10,
    verbose: bool = False
) -> list[dict]:
    """
    Fetch metadata from multiple URLs.

    Args:
        urls: List of URLs.
        timeout: Request timeout.
        verbose: Print progress.

    Returns:
        List of metadata dictionaries.
    """
    results = []
    for i, url in enumerate(urls, 1):
        if verbose:
            print(f"[{i}/{len(urls)}] Fetching: {url}")

        metadata = fetch_metadata(url, timeout)
        results.append(metadata)

        if verbose:
            print(f"  Title: {metadata.get('title') or 'N/A'}")

    return results


def format_result_human(result: dict) -> str:
    """Format metadata for human-readable output."""
    lines = []
    lines.append(f"URL: {result['url']}")

    if result.get('error'):
        lines.append(f"Error: {result['error']}")
        return '\n'.join(lines)

    if result.get('title'):
        lines.append(f"Title: {result['title']}")

    if result.get('description'):
        lines.append(f"Description: {result['description']}")

    if result.get('og_title'):
        lines.append(f"OG Title: {result['og_title']}")

    if result.get('og_image'):
        lines.append(f"OG Image: {result['og_image']}")

    if result.get('favicon'):
        lines.append(f"Favicon: {result['favicon']}")

    if result.get('h1'):
        lines.append(f"H1: {result['h1']}")

    if result.get('images'):
        lines.append(f"Images: {len(result['images'])} found")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch metadata from URLs."
    )
    parser.add_argument(
        "-u", "--url",
        type=str,
        help="URL to fetch metadata from"
    )
    parser.add_argument(
        "-f", "--file",
        type=str,
        help="File with URLs (one per line)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Request timeout in seconds (default: 10)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print progress information"
    )

    args = parser.parse_args()

    if not args.url and not args.file:
        parser.error("Either --url or --file is required")

    # Get URLs
    urls = []
    if args.url:
        urls.append(args.url)
    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            urls.extend(line.strip() for line in f if line.strip())

    # Fetch metadata
    results = fetch_metadata_batch(urls, timeout=args.timeout, verbose=args.verbose)

    # Output
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for i, result in enumerate(results):
            if i > 0:
                print("\n" + "-" * 50)
            print(format_result_human(result))


if __name__ == "__main__":
    main()