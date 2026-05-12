#!/usr/bin/env python3
"""
Port Scanner Tool
Scan open ports on a host.
"""

import argparse
import json
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional


# Common ports and their services
COMMON_PORTS = {
    20: 'FTP Data',
    21: 'FTP',
    22: 'SSH',
    23: 'Telnet',
    25: 'SMTP',
    53: 'DNS',
    67: 'DHCP',
    68: 'DHCP',
    69: 'TFTP',
    80: 'HTTP',
    110: 'POP3',
    119: 'NNTP',
    123: 'NTP',
    135: 'RPC',
    137: 'NetBIOS',
    138: 'NetBIOS',
    139: 'NetBIOS',
    143: 'IMAP',
    161: 'SNMP',
    162: 'SNMP Trap',
    389: 'LDAP',
    443: 'HTTPS',
    445: 'SMB',
    465: 'SMTPS',
    514: 'Syslog',
    587: 'SMTP TLS',
    636: 'LDAPS',
    993: 'IMAPS',
    995: 'POP3S',
    1080: 'SOCKS',
    1433: 'MSSQL',
    1434: 'MSSQL',
    1521: 'Oracle',
    1723: 'PPTP',
    2049: 'NFS',
    3306: 'MySQL',
    3389: 'RDP',
    5432: 'PostgreSQL',
    5900: 'VNC',
    5901: 'VNC',
    6379: 'Redis',
    8080: 'HTTP Proxy',
    8443: 'HTTPS Alt',
    9000: 'PHP-FPM',
    9090: 'Prometheus',
    27017: 'MongoDB',
}


def scan_port(host: str, port: int, timeout: float = 1.0) -> Optional[dict]:
    """
    Scan a single port on a host.

    Args:
        host: Hostname or IP address.
        port: Port number to scan.
        timeout: Connection timeout in seconds.

    Returns:
        Dictionary with port info if open, None if closed.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))

        if result == 0:
            # Port is open, try to get banner
            banner = None
            try:
                sock.send(b'HEAD / HTTP/1.0\r\n\r\n')
                banner = sock.recv(1024).decode('utf-8', errors='ignore').strip()
            except:
                pass

            sock.close()

            return {
                'port': port,
                'service': COMMON_PORTS.get(port, 'Unknown'),
                'banner': banner[:100] if banner else None
            }
        else:
            sock.close()
            return None

    except socket.gaierror:
        raise ValueError(f"Cannot resolve hostname: {host}")
    except socket.error:
        return None


def parse_port_range(port_str: str) -> list[int]:
    """
    Parse port specification into list of ports.

    Args:
        port_str: Port range like "1-1000" or "80,443,22" or "22".

    Returns:
        List of port numbers.
    """
    ports = []

    if '-' in port_str:
        # Range: 1-1000
        start, end = port_str.split('-')
        ports = list(range(int(start), int(end) + 1))
    elif ',' in port_str:
        # List: 80,443,22
        ports = [int(p.strip()) for p in port_str.split(',')]
    else:
        # Single port
        ports = [int(port_str)]

    return sorted(set(p for p in ports if 1 <= p <= 65535))


def scan_ports(
    host: str,
    ports: list[int],
    timeout: float = 1.0,
    threads: int = 100,
    verbose: bool = False
) -> list[dict]:
    """
    Scan multiple ports on a host.

    Args:
        host: Hostname or IP address.
        ports: List of ports to scan.
        timeout: Connection timeout.
        threads: Number of threads.
        verbose: Print progress.

    Returns:
        List of open ports with info.
    """
    open_ports = []

    if verbose:
        print(f"Scanning {host}...")
        print(f"Ports to scan: {len(ports)}")
        print(f"Threads: {threads}")

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {
            executor.submit(scan_port, host, port, timeout): port
            for port in ports
        }

        completed = 0
        for future in as_completed(futures):
            completed += 1
            if verbose and completed % 100 == 0:
                print(f"Progress: {completed}/{len(ports)}")

            try:
                result = future.result()
                if result:
                    open_ports.append(result)
                    if verbose:
                        print(f"  [OPEN] Port {result['port']}: {result['service']}")
            except Exception as e:
                if verbose:
                    print(f"Error: {e}")

    return sorted(open_ports, key=lambda x: x['port'])


def main():
    parser = argparse.ArgumentParser(
        description="Scan open ports on a host."
    )
    parser.add_argument(
        "-H", "--host",
        type=str,
        required=True,
        help="Target host or IP address"
    )
    parser.add_argument(
        "-p", "--ports",
        type=str,
        default="1-1024",
        help="Port range (e.g., '1-1000', '80,443,22', default: 1-1024)"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=1.0,
        help="Connection timeout in seconds (default: 1.0)"
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=100,
        help="Number of threads (default: 100)"
    )
    parser.add_argument(
        "--common",
        action="store_true",
        help="Scan only common ports (1-1024)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Scan all ports (1-65535)"
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

    # Determine port range
    if args.all:
        port_range = "1-65535"
    elif args.common:
        port_range = "1-1024"
    else:
        port_range = args.ports

    ports = parse_port_range(port_range)

    # Scan ports
    open_ports = scan_ports(
        args.host,
        ports,
        timeout=args.timeout,
        threads=args.threads,
        verbose=args.verbose
    )

    # Output results
    if args.json:
        result = {
            'host': args.host,
            'ports_scanned': len(ports),
            'open_ports': open_ports
        }
        print(json.dumps(result, indent=2))
    else:
        print(f"\nScan Results for {args.host}")
        print("=" * 50)
        if open_ports:
            print(f"{'PORT':<10} {'SERVICE':<20} {'BANNER'}")
            print("-" * 50)
            for port_info in open_ports:
                banner = port_info.get('banner', '')[:30] if port_info.get('banner') else ''
                print(f"{port_info['port']:<10} {port_info['service']:<20} {banner}")
        else:
            print("No open ports found.")

        print(f"\nScanned: {len(ports)} ports | Open: {len(open_ports)}")


if __name__ == "__main__":
    main()