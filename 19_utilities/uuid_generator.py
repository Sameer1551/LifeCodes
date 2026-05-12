#!/usr/bin/env python3
"""
uuid_generator.py

Generates UUIDs (v1, v4, v7) and ULIDs.
Bulk generation, formatting, and validation.
Cross-platform.

Usage:
    python uuid_generator.py
    python uuid_generator.py --count 100
    python uuid_generator.py --format ulid
    python uuid_generator.py --count 50 --format both
    python uuid_generator.py --validate "550e8400-e29b-41d4-a716-446655440000"
"""

from __future__ import annotations

import argparse
import re
import time
import uuid as _uuid
from pathlib import Path
from typing import Optional


ULID_CHARS = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _encode_time_ms(ms: int) -> str:
    d = []
    for _ in range(10):
        d.insert(0, ms & 31)
        ms >>= 5
    return "".join(ULID_CHARS[x] for x in d)


def _random_base32(size: int) -> str:
    import os as _os
    data = _os.urandom(size)
    return "".join(ULID_CHARS[b & 31] for b in data)


def _encode_crockford(b: str) -> str:
    return b


def generate_uuid(uuid_format: str = "v4", count: int = 1) -> list[str]:
    results = []
    for _ in range(count):
        if uuid_format == "v1":
            results.append(str(_uuid.uuid1()))
        elif uuid_format == "v4":
            results.append(str(_uuid.uuid4()))
        elif uuid_format == "v7":
            ts_ms = int(time.time() * 1000)
            ts_bytes = ts_ms.to_bytes(6, "big")
            rand_bytes = _uuid.uuid4().bytes[:10]
            results.append(str(_uuid.UUID(bytes=ts_bytes + rand_bytes, version=7)))
        elif uuid_format == "ulid":
            now_ms = int(time.time() * 1000)
            time_part = _encode_time_ms(now_ms)
            rand_part = _random_base32(10)
            results.append(time_part + rand_part)
        else:
            results.append(str(_uuid.uuid4()))
    return results


UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)


def validate(value: str) -> tuple[bool, str]:
    v = value.strip()
    if UUID_RE.match(v):
        try:
            _uuid.UUID(v)
            return True, "UUID"
        except ValueError:
            return False, "invalid UUID format"
    if len(v) == 26:
        return True, "ULID"
    return False, "unknown format"


def main() -> None:
    parser = argparse.ArgumentParser(description="UUID/ULID Generator")
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--format", choices=["v1", "v4", "v7", "ulid", "both"], default="v4")
    parser.add_argument("--out", help="Output file")
    parser.add_argument("--validate", help="Validate a UUID/ULID")
    parser.add_argument("--upper", action="store_true")
    args = parser.parse_args()

    if args.validate:
        ok, fmt = validate(args.validate)
        print(f"Valid {fmt}: {args.validate}" if ok else f"Invalid: {args.validate}")
        return

    formats = [args.format] if args.format != "both" else ["v4", "ulid"]
    all_results = []
    for fmt in formats:
        all_results.extend(generate_uuid(fmt, args.count))

    if args.upper:
        all_results = [r.upper() for r in all_results]

    if args.out:
        Path(args.out).write_text("\n".join(all_results), encoding="utf-8")
        print(f"Wrote {len(all_results)} to {args.out}")
    else:
        for r in all_results:
            print(r)


if __name__ == "__main__":
    main()