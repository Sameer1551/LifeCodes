#!/usr/bin/env python3
"""
Internet Speed Test Tool
Measure internet download and upload speeds.
"""

import argparse
import json
import time

try:
    import speedtest
    HAS_SPEEDTEST = True
except ImportError:
    HAS_SPEEDTEST = False


def run_speedtest(
    test_download: bool = True,
    test_upload: bool = True,
    test_ping: bool = True,
    server_id: int | None = None
) -> dict:
    """
    Run an internet speed test.

    Args:
        test_download: Test download speed.
        test_upload: Test upload speed.
        test_ping: Test ping.
        server_id: Specific server ID to use.

    Returns:
        Dictionary with speed test results.
    """
    if not HAS_SPEEDTEST:
        raise ImportError(
            "speedtest-cli is required. Install with: pip install speedtest-cli"
        )

    st = speedtest.Speedtest()

    # Get best server
    st.get_best_server()

    results = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'server': {
            'name': st.results.server.get('name'),
            'sponsor': st.results.server.get('sponsor'),
            'url': st.results.server.get('url'),
            'latency': None
        },
        'ping_ms': None,
        'download_mbps': None,
        'upload_mbps': None
    }

    # Ping test
    if test_ping:
        print("Testing ping...")
        results['ping_ms'] = round(st.results.ping, 2)
        results['server']['latency'] = results['ping_ms']

    # Download test
    if test_download:
        print("Testing download speed...")
        st.download()
        download_bps = st.results.download
        results['download_mbps'] = round(download_bps / 1_000_000, 2)

    # Upload test
    if test_upload:
        print("Testing upload speed...")
        st.upload()
        upload_bps = st.results.upload
        results['upload_mbps'] = round(upload_bps / 1_000_000, 2)

    return results


def get_servers(limit: int = 10) -> list[dict]:
    """
    Get list of available speedtest servers.

    Args:
        limit: Maximum number of servers to return.

    Returns:
        List of server dictionaries.
    """
    if not HAS_SPEEDTEST:
        raise ImportError("speedtest-cli is required")

    st = speedtest.Speedtest()
    servers = st.get_servers()

    server_list = []
    for server_group in servers.values():
        for server in server_group[:limit]:
            server_list.append({
                'id': server.get('id'),
                'name': server.get('name'),
                'sponsor': server.get('sponsor'),
                'country': server.get('country'),
                'distance_km': round(server.get('d', 0), 2)
            })

    return sorted(server_list, key=lambda x: x['distance_km'])[:limit]


def format_results_human(results: dict) -> str:
    """Format speed test results for human-readable output."""
    lines = [
        "Internet Speed Test Results",
        "=" * 40,
        f"Time: {results['timestamp']}",
        f"Server: {results['server']['sponsor']} ({results['server']['name']})",
    ]

    if results['ping_ms'] is not None:
        lines.append(f"Ping: {results['ping_ms']} ms")

    if results['download_mbps'] is not None:
        lines.append(f"Download: {results['download_mbps']} Mbps")

    if results['upload_mbps'] is not None:
        lines.append(f"Upload: {results['upload_mbps']} Mbps")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Test internet download and upload speeds."
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Test download speed only"
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Test upload speed only"
    )
    parser.add_argument(
        "--ping",
        action="store_true",
        help="Test ping only"
    )
    parser.add_argument(
        "--server",
        type=int,
        help="Specific server ID to use"
    )
    parser.add_argument(
        "--list-servers",
        action="store_true",
        help="List available servers"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    if not HAS_SPEEDTEST:
        print("Error: speedtest-cli is required.")
        print("Install with: pip install speedtest-cli")
        return

    if args.list_servers:
        servers = get_servers()
        if args.json:
            print(json.dumps(servers, indent=2))
        else:
            print("Available Speedtest Servers")
            print("=" * 60)
            print(f"{'ID':<8} {'Sponsor':<25} {'Country':<10} {'Distance'}")
            print("-" * 60)
            for server in servers:
                print(f"{server['id']:<8} {server['sponsor']:<25} {server['country']:<10} {server['distance_km']} km")
        return

    # Determine which tests to run
    test_download = not (args.upload or args.ping) or args.download
    test_upload = not (args.download or args.ping) or args.upload
    test_ping = not (args.download or args.upload) or args.ping

    print("Running speed test... (this may take a minute)\n")

    try:
        results = run_speedtest(
            test_download=test_download,
            test_upload=test_upload,
            test_ping=test_ping,
            server_id=args.server
        )

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(format_results_human(results))

    except Exception as e:
        print(f"Error running speed test: {e}")


if __name__ == "__main__":
    main()