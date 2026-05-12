#!/usr/bin/env python3
"""
Proxy Checker Tool
Validate and test proxy servers.
"""

import argparse
import json
import time
from urllib.parse import urlparse

import requests


def check_proxy(
    proxy_url: str,
    test_url: str = 'http://httpbin.org/ip',
    timeout: int = 10
) -> dict:
    """
    Check if a proxy is working.

    Args:
        proxy_url: Proxy URL (http://host:port or socks5://host:port).
        test_url: URL to test proxy against.
        timeout: Request timeout.

    Returns:
        Dictionary with proxy status.
    """
    result = {
        'proxy': proxy_url,
        'working': False,
        'response_time_ms': None,
        'ip_address': None,
        'anonymous': None,
        'error': None
    }

    # Parse proxy URL
    if not proxy_url.startswith(('http://', 'https://', 'socks4://', 'socks5://', 'socks://')):
        proxy_url = 'http://' + proxy_url

    proxies = {
        'http': proxy_url,
        'https': proxy_url
    }

    start_time = time.time()

    try:
        # Test the proxy
        response = requests.get(
            test_url,
            proxies=proxies,
            timeout=timeout,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; ProxyChecker/1.0)'}
        )

        end_time = time.time()
        result['response_time_ms'] = round((end_time - start_time) * 1000, 2)

        if response.status_code == 200:
            result['working'] = True

            # Try to get IP from response
            try:
                data = response.json()
                result['ip_address'] = data.get('origin') or data.get('ip')
            except:
                result['ip_address'] = 'Unknown'

            # Check if anonymous (doesn't reveal real IP)
            headers_response = requests.get(
                'http://httpbin.org/headers',
                proxies=proxies,
                timeout=timeout
            )
            if headers_response.status_code == 200:
                headers = headers_response.json().get('headers', {})
                # If X-Forwarded-For or similar headers are present, not fully anonymous
                anonymous_headers = ['X-Forwarded-For', 'X-Real-Ip', 'Via']
                result['anonymous'] = not any(h in headers for h in anonymous_headers)

    except requests.ProxyError as e:
        result['error'] = f'Proxy error: {str(e)[:100]}'
    except requests.Timeout:
        result['error'] = f'Timeout after {timeout}s'
    except requests.RequestException as e:
        result['error'] = str(e)[:100]
    except Exception as e:
        result['error'] = str(e)[:100]

    return result


def check_proxies_batch(
    proxy_list: list[str],
    test_url: str = 'http://httpbin.org/ip',
    timeout: int = 10,
    verbose: bool = False
) -> list[dict]:
    """
    Check multiple proxies.

    Args:
        proxy_list: List of proxy URLs.
        test_url: URL to test against.
        timeout: Request timeout.
        verbose: Print progress.

    Returns:
        List of proxy check results.
    """
    results = []

    for i, proxy in enumerate(proxy_list, 1):
        if verbose:
            print(f"[{i}/{len(proxy_list)}] Checking: {proxy}")

        result = check_proxy(proxy, test_url, timeout)
        results.append(result)

        if verbose:
            status = '✓' if result['working'] else '✗'
            info = f"{result['response_time_ms']}ms" if result['working'] else result['error'][:30]
            print(f"  {status} {info}")

    return results


def load_proxies_from_file(file_path: str) -> list[str]:
    """Load proxies from file (one per line)."""
    proxies = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                proxies.append(line)
    return proxies


def format_result_human(result: dict) -> str:
    """Format proxy result for human-readable output."""
    lines = [f"Proxy: {result['proxy']}"]

    if result['working']:
        lines.append(f"Status: WORKING ✓")
        lines.append(f"Response Time: {result['response_time_ms']}ms")
        if result['ip_address']:
            lines.append(f"IP Address: {result['ip_address']}")
        if result['anonymous'] is not None:
            anon_status = 'Anonymous' if result['anonymous'] else 'Transparent'
            lines.append(f"Type: {anon_status}")
    else:
        lines.append(f"Status: NOT WORKING ✗")
        if result['error']:
            lines.append(f"Error: {result['error']}")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Check and validate proxy servers."
    )
    parser.add_argument(
        "-p", "--proxy",
        type=str,
        help="Proxy URL (http://host:port or socks5://host:port)"
    )
    parser.add_argument(
        "-f", "--file",
        type=str,
        help="File with proxy URLs (one per line)"
    )
    parser.add_argument(
        "--test-url",
        type=str,
        default='http://httpbin.org/ip',
        help="URL to test proxy against (default: httpbin.org/ip)"
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

    if not args.proxy and not args.file:
        parser.error("Either --proxy or --file is required")

    # Get proxies
    proxies = []
    if args.proxy:
        proxies.append(args.proxy)
    if args.file:
        proxies.extend(load_proxies_from_file(args.file))

    # Check proxies
    results = check_proxies_batch(
        proxies,
        test_url=args.test_url,
        timeout=args.timeout,
        verbose=args.verbose
    )

    # Output
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for i, result in enumerate(results):
            if i > 0:
                print("\n" + "-" * 40)
            print(format_result_human(result))

    # Summary
    working = sum(1 for r in results if r['working'])
    print(f"\nSummary: {working}/{len(results)} proxies working")

    if working > 0:
        avg_time = sum(r['response_time_ms'] for r in results if r['working']) / working
        print(f"Average response time: {round(avg_time, 2)}ms")


if __name__ == "__main__":
    main()