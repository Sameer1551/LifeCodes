#!/usr/bin/env python3
"""
Network Latency Checker Tool
Ping servers and measure network latency.
"""

import argparse
import json
import platform
import re
import socket
import subprocess
import time
from typing import Optional


def ping_host(host: str, count: int = 4, timeout: int = 2) -> dict:
    """
    Ping a host and measure latency.

    Args:
        host: Hostname or IP address.
        count: Number of ping packets.
        timeout: Timeout for each ping.

    Returns:
        Dictionary with ping statistics.
    """
    # Determine ping command based on OS
    system = platform.system().lower()

    if system == 'windows':
        cmd = ['ping', '-n', str(count), '-w', str(timeout * 1000), host]
    else:
        cmd = ['ping', '-c', str(count), '-W', str(timeout), host]

    result = {
        'host': host,
        'packets_sent': count,
        'packets_received': 0,
        'packet_loss_pct': 100,
        'latency_min_ms': None,
        'latency_avg_ms': None,
        'latency_max_ms': None,
        'latencies_ms': [],
        'reachable': False,
        'error': None
    }

    try:
        output = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=count * timeout + 5
        )
        ping_output = output.stdout

        # Parse ping output
        if system == 'windows':
            # Windows ping output parsing
            match = re.search(r'Received = (\d+)', ping_output)
            if match:
                result['packets_received'] = int(match.group(1))

            match = re.search(r'Minimum = (\d+).*Maximum = (\d+).*Average = (\d+)', ping_output, re.DOTALL)
            if match:
                result['latency_min_ms'] = float(match.group(1))
                result['latency_avg_ms'] = float(match.group(3))
                result['latency_max_ms'] = float(match.group(2))

            # Extract individual latencies
            latencies = re.findall(r'time[=<](\d+)', ping_output)
            result['latencies_ms'] = [float(l) for l in latencies]
        else:
            # Unix ping output parsing
            match = re.search(r'(\d+) packets?.*?(\d+) received', ping_output)
            if match:
                result['packets_sent'] = int(match.group(1))
                result['packets_received'] = int(match.group(2))

            match = re.search(r'rtt.*?= ([\d.]+)/([\d.]+)/([\d.]+)', ping_output)
            if match:
                result['latency_min_ms'] = float(match.group(1))
                result['latency_avg_ms'] = float(match.group(2))
                result['latency_max_ms'] = float(match.group(3))

            # Extract individual latencies
            latencies = re.findall(r'time=([\d.]+)', ping_output)
            result['latencies_ms'] = [float(l) for l in latencies]

        # Calculate packet loss
        if result['packets_sent'] > 0:
            result['packet_loss_pct'] = round(
                (result['packets_sent'] - result['packets_received']) / result['packets_sent'] * 100, 2
            )

        result['reachable'] = result['packets_received'] > 0

    except subprocess.TimeoutExpired:
        result['error'] = 'Ping timed out'
    except FileNotFoundError:
        result['error'] = 'Ping command not found'
    except Exception as e:
        result['error'] = str(e)

    return result


def tcp_ping(host: str, port: int, timeout: float = 2.0) -> dict:
    """
    Test TCP connectivity to a host and port.

    Args:
        host: Hostname or IP address.
        port: Port number.
        timeout: Connection timeout.

    Returns:
        Dictionary with connection info.
    """
    result = {
        'host': host,
        'port': port,
        'reachable': False,
        'latency_ms': None,
        'error': None
    }

    start_time = time.time()

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)

        result['reachable'] = sock.connect_ex((host, port)) == 0
        end_time = time.time()

        if result['reachable']:
            result['latency_ms'] = round((end_time - start_time) * 1000, 2)

        sock.close()

    except socket.gaierror:
        result['error'] = f'Cannot resolve hostname: {host}'
    except socket.error as e:
        result['error'] = str(e)

    return result


def ping_multiple_hosts(
    hosts: list[str],
    count: int = 4,
    timeout: int = 2,
    tcp_port: int | None = None,
    verbose: bool = False
) -> list[dict]:
    """
    Ping multiple hosts.

    Args:
        hosts: List of hosts to ping.
        count: Ping count.
        timeout: Timeout.
        tcp_port: Port for TCP ping (optional).
        verbose: Print progress.

    Returns:
        List of ping results.
    """
    results = []

    for i, host in enumerate(hosts, 1):
        if verbose:
            print(f"[{i}/{len(hosts)}] Pinging: {host}")

        if tcp_port:
            result = tcp_ping(host, tcp_port, timeout)
        else:
            result = ping_host(host, count, timeout)

        results.append(result)

        if verbose:
            status = '✓' if result['reachable'] else '✗'
            if tcp_port:
                latency = f"{result['latency_ms']}ms" if result['latency_ms'] else 'N/A'
                print(f"  {status} Port {tcp_port}: {latency}")
            else:
                avg = f"{result['latency_avg_ms']}ms" if result['latency_avg_ms'] else 'N/A'
                loss = f"{result['packet_loss_pct']}% loss"
                print(f"  {status} Avg: {avg}, {loss}")

    return results


def format_result_human(result: dict, tcp_mode: bool = False) -> str:
    """Format ping result for human-readable output."""
    lines = [f"Host: {result['host']}"]

    if result.get('error'):
        lines.append(f"Error: {result['error']}")
        return '\n'.join(lines)

    if tcp_mode:
        status = 'OPEN' if result['reachable'] else 'CLOSED'
        lines.append(f"Port {result['port']}: {status}")
        if result['latency_ms']:
            lines.append(f"Latency: {result['latency_ms']}ms")
    else:
        status = 'REACHABLE' if result['reachable'] else 'UNREACHABLE'
        lines.append(f"Status: {status}")
        lines.append(f"Packets: {result['packets_received']}/{result['packets_sent']} received")
        lines.append(f"Packet Loss: {result['packet_loss_pct']}%")

        if result['latency_avg_ms']:
            lines.append(f"Latency: min={result['latency_min_ms']}ms, avg={result['latency_avg_ms']}ms, max={result['latency_max_ms']}ms")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Ping servers and measure network latency."
    )
    parser.add_argument(
        "-H", "--host",
        type=str,
        help="Host to ping"
    )
    parser.add_argument(
        "-f", "--file",
        type=str,
        help="File with hosts to ping (one per line)"
    )
    parser.add_argument(
        "-c", "--count",
        type=int,
        default=4,
        help="Number of ping packets (default: 4)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=2,
        help="Timeout per ping in seconds (default: 2)"
    )
    parser.add_argument(
        "--tcp",
        action="store_true",
        help="Use TCP ping instead of ICMP"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=80,
        help="Port for TCP ping (default: 80)"
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

    if not args.host and not args.file:
        parser.error("Either --host or --file is required")

    # Get hosts
    hosts = []
    if args.host:
        hosts.append(args.host)
    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            hosts.extend(line.strip() for line in f if line.strip())

    # Ping hosts
    results = ping_multiple_hosts(
        hosts,
        count=args.count,
        timeout=args.timeout,
        tcp_port=args.port if args.tcp else None,
        verbose=args.verbose
    )

    # Output
    if args.json:
        output = {'results': results, 'tcp_mode': args.tcp}
        print(json.dumps(output, indent=2))
    else:
        for i, result in enumerate(results):
            if i > 0:
                print("\n" + "-" * 40)
            print(format_result_human(result, tcp_mode=args.tcp))

    # Summary
    reachable = sum(1 for r in results if r['reachable'])
    print(f"\nSummary: {reachable}/{len(results)} hosts reachable")


if __name__ == "__main__":
    main()