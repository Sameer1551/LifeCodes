#!/usr/bin/env python3
"""
IP Geolocation Tool
Find geographic location of an IP address.
"""

import argparse
import json
import requests
from typing import Optional


def get_public_ip() -> Optional[str]:
    """Get the current public IP address."""
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=10)
        return response.json()['ip']
    except Exception:
        return None


def get_geolocation(ip: str = None) -> dict:
    """
    Get geolocation data for an IP address.

    Uses free API from ip-api.com (no API key required, 45 requests/minute limit).

    Args:
        ip: IP address to locate, or None for current IP.

    Returns:
        Dictionary with geolocation data.
    """
    # Use ip-api.com free API
    if ip is None:
        url = "http://ip-api.com/json/"
    else:
        url = f"http://ip-api.com/json/{ip}"

    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        if data.get('status') == 'fail':
            return {
                'success': False,
                'ip': ip or 'unknown',
                'error': data.get('message', 'Unknown error')
            }

        return {
            'success': True,
            'ip': data.get('query'),
            'country': data.get('country'),
            'country_code': data.get('countryCode'),
            'region': data.get('regionName'),
            'city': data.get('city'),
            'zip': data.get('zip'),
            'lat': data.get('lat'),
            'lon': data.get('lon'),
            'timezone': data.get('timezone'),
            'isp': data.get('isp'),
            'org': data.get('org'),
            'as': data.get('as'),
            'mobile': data.get('mobile', False),
            'proxy': data.get('proxy', False),
            'hosting': data.get('hosting', False)
        }

    except requests.RequestException as e:
        return {
            'success': False,
            'ip': ip or 'unknown',
            'error': str(e)
        }


def get_geolocation_batch(ips: list[str]) -> list[dict]:
    """
    Get geolocation for multiple IPs.

    Args:
        ips: List of IP addresses.

    Returns:
        List of geolocation dictionaries.
    """
    results = []
    for ip in ips:
        result = get_geolocation(ip)
        results.append(result)
    return results


def format_result_human(result: dict) -> str:
    """Format geolocation result for human-readable output."""
    if not result.get('success'):
        return f"IP: {result.get('ip', 'unknown')}\nError: {result.get('error', 'Unknown error')}"

    lines = [
        f"IP: {result['ip']}",
        f"Location: {result['city']}, {result['region']}, {result['country']} ({result['country_code']})",
        f"Coordinates: {result['lat']}, {result['lon']}",
        f"Timezone: {result['timezone']}",
        f"ISP: {result['isp']}",
        f"Organization: {result['org']}",
        f"AS: {result['as']}",
    ]

    flags = []
    if result.get('mobile'):
        flags.append('Mobile')
    if result.get('proxy'):
        flags.append('Proxy')
    if result.get('hosting'):
        flags.append('Hosting')

    if flags:
        lines.append(f"Type: {', '.join(flags)}")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Find geographic location of an IP address."
    )
    parser.add_argument(
        "-i", "--ip",
        type=str,
        help="IP address to locate"
    )
    parser.add_argument(
        "-f", "--file",
        type=str,
        help="File with IP addresses (one per line)"
    )
    parser.add_argument(
        "--my-ip",
        action="store_true",
        help="Get location of your public IP"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format"
    )

    args = parser.parse_args()

    if not args.ip and not args.file and not args.my_ip:
        # Default to showing current IP location
        args.my_ip = True

    # Get IPs to look up
    ips = []
    if args.ip:
        ips.append(args.ip)
    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            ips.extend(line.strip() for line in f if line.strip())
    if args.my_ip:
        my_ip = get_public_ip()
        if my_ip:
            ips.insert(0, my_ip)
            print(f"Your public IP: {my_ip}\n")

    # Get geolocation
    results = get_geolocation_batch(ips)

    # Output results
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for i, result in enumerate(results):
            if i > 0:
                print("\n" + "-" * 50)
            print(format_result_human(result))


if __name__ == "__main__":
    main()