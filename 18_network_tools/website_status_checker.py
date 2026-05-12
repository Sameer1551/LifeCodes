#!/usr/bin/env python3
"""
Website Status Checker Tool
Check uptime and status of websites.
"""

import argparse
import json
import time
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def create_session_with_retries(
    retries: int = 3,
    backoff_factor: float = 0.3
) -> requests.Session:
    """Create a requests session with retry logic."""
    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def check_website(
    url: str,
    timeout: int = 10,
    follow_redirects: bool = True,
    verify_ssl: bool = True
) -> dict:
    """
    Check the status of a website.

    Args:
        url: URL to check.
        timeout: Request timeout in seconds.
        follow_redirects: Whether to follow redirects.
        verify_ssl: Whether to verify SSL certificates.

    Returns:
        Dictionary with status information.
    """
    # Ensure URL has scheme
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    result = {
        'url': url,
        'status_code': None,
        'status': 'unknown',
        'response_time_ms': None,
        'redirect_chain': [],
        'final_url': url,
        'error': None,
        'headers': {}
    }

    session = create_session_with_retries()
    start_time = time.time()

    try:
        response = session.get(
            url,
            timeout=timeout,
            allow_redirects=follow_redirects,
            verify=verify_ssl,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; StatusChecker/1.0)'}
        )

        end_time = time.time()
        result['response_time_ms'] = round((end_time - start_time) * 1000, 2)
        result['status_code'] = response.status_code
        result['final_url'] = response.url
        result['headers'] = dict(response.headers)

        # Capture redirect chain
        if response.history:
            result['redirect_chain'] = [
                {'url': r.url, 'status': r.status_code}
                for r in response.history
            ]

        # Determine status
        if 200 <= response.status_code < 300:
            result['status'] = 'up'
        elif 300 <= response.status_code < 400:
            result['status'] = 'redirect'
        elif 400 <= response.status_code < 500:
            result['status'] = 'client_error'
        else:
            result['status'] = 'server_error'

    except requests.exceptions.Timeout:
        result['status'] = 'timeout'
        result['error'] = f'Request timed out after {timeout}s'
    except requests.exceptions.ConnectionError as e:
        result['status'] = 'down'
        result['error'] = str(e)
    except requests.exceptions.SSLError as e:
        result['status'] = 'ssl_error'
        result['error'] = str(e)
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
    finally:
        session.close()

    return result


def check_websites_batch(
    urls: list[str],
    timeout: int = 10,
    follow_redirects: bool = True,
    verbose: bool = False
) -> list[dict]:
    """
    Check multiple websites.

    Args:
        urls: List of URLs to check.
        timeout: Request timeout in seconds.
        follow_redirects: Whether to follow redirects.
        verbose: Print progress information.

    Returns:
        List of status dictionaries.
    """
    results = []
    for i, url in enumerate(urls, 1):
        if verbose:
            print(f"[{i}/{len(urls)}] Checking: {url}")

        result = check_website(url, timeout, follow_redirects)
        results.append(result)

        if verbose:
            status_icon = '✓' if result['status'] == 'up' else '✗'
            print(f"  {status_icon} Status: {result['status']} ({result['status_code'] or 'N/A'})")

    return results


def format_result_human(result: dict) -> str:
    """Format a single result for human-readable output."""
    lines = []
    lines.append(f"URL: {result['url']}")

    if result['error']:
        lines.append(f"Status: {result['status'].upper()}")
        lines.append(f"Error: {result['error']}")
    else:
        lines.append(f"Status: {result['status'].upper()}")
        lines.append(f"Status Code: {result['status_code']}")
        lines.append(f"Response Time: {result['response_time_ms']}ms")
        lines.append(f"Final URL: {result['final_url']}")

        if result['redirect_chain']:
            lines.append(f"Redirects: {len(result['redirect_chain'])}")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Check website uptime and status."
    )
    parser.add_argument(
        "-u", "--url",
        type=str,
        help="URL to check"
    )
    parser.add_argument(
        "-f", "--file",
        type=str,
        help="File with URLs to check (one per line)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Request timeout in seconds (default: 10)"
    )
    parser.add_argument(
        "--no-redirects",
        action="store_true",
        help="Don't follow redirects"
    )
    parser.add_argument(
        "--no-verify-ssl",
        action="store_true",
        help="Don't verify SSL certificates"
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

    # Get URLs to check
    urls = []
    if args.url:
        urls.append(args.url)
    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            urls.extend(line.strip() for line in f if line.strip())

    # Check websites
    results = check_websites_batch(
        urls,
        timeout=args.timeout,
        follow_redirects=not args.no_redirects,
        verbose=args.verbose
    )

    # Output results
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for result in results:
            print("-" * 50)
            print(format_result_human(result))

    # Summary
    up_count = sum(1 for r in results if r['status'] == 'up')
    print(f"\nSummary: {up_count}/{len(results)} websites are UP")


if __name__ == "__main__":
    main()