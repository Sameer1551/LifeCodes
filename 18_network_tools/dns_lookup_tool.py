#!/usr/bin/env python3
"""
DNS Lookup Tool
Resolve domain names to IP addresses and other DNS records.
"""

import argparse
import json
import socket

try:
    import dns.resolver
    import dns.reversename
    import dns.exception
    HAS_DNSPYTHON = True
except ImportError:
    HAS_DNSPYTHON = False


RECORD_TYPES = ['A', 'AAAA', 'MX', 'NS', 'TXT', 'CNAME', 'SOA', 'SRV', 'PTR']


def lookup_record(domain: str, record_type: str = 'A') -> list[str]:
    """
    Look up DNS records for a domain.

    Args:
        domain: Domain name to lookup.
        record_type: DNS record type (A, AAAA, MX, NS, TXT, etc.).

    Returns:
        List of record values.
    """
    if not HAS_DNSPYTHON:
        # Fallback to socket for basic lookups
        try:
            if record_type == 'A':
                result = socket.getaddrinfo(domain, None, socket.AF_INET)
                return [r[4][0] for r in result]
            elif record_type == 'AAAA':
                result = socket.getaddrinfo(domain, None, socket.AF_INET6)
                return [r[4][0] for r in result]
            else:
                return [f"dnspython required for {record_type} records"]
        except socket.gaierror:
            return []

    results = []
    try:
        answers = dns.resolver.resolve(domain, record_type)
        for rdata in answers:
            if record_type == 'MX':
                results.append(f"{rdata.preference} {rdata.exchange}")
            elif record_type == 'SOA':
                results.append(f"mname={rdata.mname} rname={rdata.rname}")
            elif record_type == 'SRV':
                results.append(f"priority={rdata.priority} weight={rdata.weight} port={rdata.port} target={rdata.target}")
            else:
                results.append(str(rdata))
    except dns.resolver.NoAnswer:
        pass
    except dns.resolver.NXDOMAIN:
        raise ValueError(f"Domain {domain} does not exist")
    except dns.exception.DNSException:
        pass

    return results


def reverse_lookup(ip_address: str) -> list[str]:
    """
    Perform reverse DNS lookup (IP to domain).

    Args:
        ip_address: IP address to lookup.

    Returns:
        List of domain names.
    """
    if not HAS_DNSPYTHON:
        try:
            result = socket.gethostbyaddr(ip_address)
            return [result[0]] + result[1]
        except socket.herror:
            return []

    results = []
    try:
        addr = dns.reversename.from_address(ip_address)
        answers = dns.resolver.resolve(addr, 'PTR')
        for rdata in answers:
            results.append(str(rdata))
    except dns.exception.DNSException:
        pass

    return results


def lookup_domain(
    domain: str,
    record_types: list[str] | None = None
) -> dict:
    """
    Look up all DNS records for a domain.

    Args:
        domain: Domain name to lookup.
        record_types: List of record types to query.

    Returns:
        Dictionary with DNS records.
    """
    if record_types is None:
        record_types = ['A', 'AAAA', 'MX', 'NS', 'TXT']

    results = {
        'domain': domain,
        'records': {}
    }

    for rtype in record_types:
        try:
            records = lookup_record(domain, rtype)
            if records:
                results['records'][rtype] = records
        except ValueError as e:
            results['error'] = str(e)
            break
        except Exception as e:
            pass

    return results


def format_results_human(result: dict) -> str:
    """Format DNS results for human-readable output."""
    lines = []
    lines.append(f"Domain: {result['domain']}")
    lines.append("=" * 50)

    if 'error' in result:
        lines.append(f"Error: {result['error']}")
        return '\n'.join(lines)

    for rtype, records in result.get('records', {}).items():
        lines.append(f"\n{rtype} Records:")
        for record in records:
            lines.append(f"  {record}")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="DNS lookup tool for resolving domains and IPs."
    )
    parser.add_argument(
        "-d", "--domain",
        type=str,
        help="Domain name to lookup"
    )
    parser.add_argument(
        "-i", "--ip",
        type=str,
        help="IP address for reverse lookup"
    )
    parser.add_argument(
        "-t", "--type",
        type=str,
        nargs='+',
        choices=RECORD_TYPES,
        help="Record types to query (default: A AAAA MX NS TXT)"
    )
    parser.add_argument(
        "--reverse",
        action="store_true",
        help="Perform reverse lookup"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Query all record types"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format"
    )

    args = parser.parse_args()

    if not args.domain and not args.ip:
        parser.error("Either --domain or --ip is required")

    if args.ip or args.reverse:
        # Reverse lookup
        target = args.ip or args.domain
        domains = reverse_lookup(target)

        if args.json:
            print(json.dumps({
                'ip': target,
                'domains': domains
            }, indent=2))
        else:
            print(f"Reverse lookup for {target}:")
            if domains:
                for domain in domains:
                    print(f"  {domain}")
            else:
                print("  No PTR records found")

    elif args.domain:
        # Forward lookup
        if args.all:
            record_types = RECORD_TYPES
        elif args.type:
            record_types = args.type
        else:
            record_types = ['A', 'AAAA', 'MX', 'NS', 'TXT']

        result = lookup_domain(args.domain, record_types)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(format_results_human(result))


if __name__ == "__main__":
    main()