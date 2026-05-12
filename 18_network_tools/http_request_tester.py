#!/usr/bin/env python3
"""
HTTP Request Tester Tool
Test REST APIs and make HTTP requests.
"""

import argparse
import json
import sys
import time

import requests
from requests.auth import HTTPBasicAuth


def make_request(
    url: str,
    method: str = 'GET',
    headers: dict | None = None,
    body: str | None = None,
    auth: tuple | None = None,
    bearer_token: str | None = None,
    timeout: int = 30,
    allow_redirects: bool = True,
    verify_ssl: bool = True
) -> dict:
    """
    Make an HTTP request.

    Args:
        url: Request URL.
        method: HTTP method (GET, POST, PUT, DELETE, PATCH).
        headers: Request headers.
        body: Request body.
        auth: Basic auth tuple (username, password).
        bearer_token: Bearer token for authorization.
        timeout: Request timeout.
        allow_redirects: Follow redirects.
        verify_ssl: Verify SSL certificates.

    Returns:
        Dictionary with response information.
    """
    # Prepare headers
    request_headers = headers or {}

    if bearer_token:
        request_headers['Authorization'] = f'Bearer {bearer_token}'

    # Prepare body
    json_body = None
    data_body = None

    if body:
        if request_headers.get('Content-Type', '').startswith('application/json'):
            try:
                json_body = json.loads(body)
            except json.JSONDecodeError:
                data_body = body
        else:
            data_body = body

    # Make request
    start_time = time.time()

    result = {
        'request': {
            'url': url,
            'method': method.upper(),
            'headers': request_headers
        },
        'response': {
            'status_code': None,
            'headers': {},
            'body': None,
            'json': None
        },
        'timing': {
            'total_ms': None,
            'size_bytes': None
        },
        'error': None
    }

    try:
        auth_obj = HTTPBasicAuth(*auth) if auth else None

        response = requests.request(
            method=method.upper(),
            url=url,
            headers=request_headers,
            json=json_body,
            data=data_body,
            auth=auth_obj,
            timeout=timeout,
            allow_redirects=allow_redirects,
            verify=verify_ssl
        )

        end_time = time.time()

        result['response']['status_code'] = response.status_code
        result['response']['headers'] = dict(response.headers)

        # Try to parse as JSON
        try:
            result['response']['json'] = response.json()
            result['response']['body'] = None  # Don't duplicate
        except:
            result['response']['body'] = response.text[:10000]  # Limit size

        result['timing']['total_ms'] = round((end_time - start_time) * 1000, 2)
        result['timing']['size_bytes'] = len(response.content)

    except requests.Timeout:
        result['error'] = f'Request timed out after {timeout}s'
    except requests.RequestException as e:
        result['error'] = str(e)
    except Exception as e:
        result['error'] = str(e)

    return result


def parse_headers(header_list: list[str]) -> dict:
    """Parse header strings into dictionary."""
    headers = {}
    for h in header_list:
        if ':' in h:
            key, value = h.split(':', 1)
            headers[key.strip()] = value.strip()
    return headers


def format_response_human(result: dict) -> str:
    """Format response for human-readable output."""
    lines = []

    # Request info
    lines.append(f"Request: {result['request']['method']} {result['request']['url']}")

    if result.get('error'):
        lines.append(f"\nError: {result['error']}")
        return '\n'.join(lines)

    # Response info
    status_code = result['response']['status_code']
    status_icon = '✓' if status_code and 200 <= status_code < 300 else '✗'

    lines.append(f"\nStatus: {status_code} {status_icon}")
    lines.append(f"Time: {result['timing']['total_ms']}ms")
    lines.append(f"Size: {result['timing']['size_bytes']} bytes")

    # Headers
    lines.append("\nResponse Headers:")
    for key, value in list(result['response']['headers'].items())[:10]:
        lines.append(f"  {key}: {value}")

    # Body
    lines.append("\nResponse Body:")
    if result['response']['json']:
        lines.append(json.dumps(result['response']['json'], indent=2)[:2000])
    elif result['response']['body']:
        lines.append(result['response']['body'][:2000])

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Test REST APIs and make HTTP requests."
    )
    parser.add_argument(
        "-u", "--url",
        type=str,
        required=True,
        help="Request URL"
    )
    parser.add_argument(
        "-m", "--method",
        type=str,
        default='GET',
        choices=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'],
        help="HTTP method (default: GET)"
    )
    parser.add_argument(
        "-H", "--header",
        type=str,
        action='append',
        help="Request header (key:value format, can be repeated)"
    )
    parser.add_argument(
        "-d", "--data",
        type=str,
        help="Request body"
    )
    parser.add_argument(
        "--auth",
        type=str,
        help="Basic auth (username:password)"
    )
    parser.add_argument(
        "--bearer",
        type=str,
        help="Bearer token for authorization"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)"
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
        "-o", "--output",
        type=str,
        help="Save response body to file"
    )
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Output full result as JSON"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # Parse headers
    headers = parse_headers(args.header) if args.header else {}

    # Parse auth
    auth = None
    if args.auth:
        if ':' in args.auth:
            auth = tuple(args.auth.split(':', 1))
        else:
            print("Error: --auth must be in format 'username:password'")
            sys.exit(1)

    # Make request
    result = make_request(
        url=args.url,
        method=args.method,
        headers=headers,
        body=args.data,
        auth=auth,
        bearer_token=args.bearer,
        timeout=args.timeout,
        allow_redirects=not args.no_redirects,
        verify_ssl=not args.no_verify_ssl
    )

    # Save to file if requested
    if args.output:
        if result['response']['json']:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result['response']['json'], f, indent=2)
        elif result['response']['body']:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(result['response']['body'])
        print(f"Response saved to {args.output}")

    # Output
    if args.json_output:
        print(json.dumps(result, indent=2))
    else:
        print(format_response_human(result))


if __name__ == "__main__":
    main()