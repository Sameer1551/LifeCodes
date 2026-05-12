#!/usr/bin/env python3
"""
log_file_analyzer.py

Parses and analyzes log files (any format).
Detects error patterns, severity levels, timestamps.
Aggregates stats, filters, and exports results.
Generalized — works with any text-based log format.

Usage:
    python log_file_analyzer.py app.log
    python log_file_analyzer.py app.log --errors
    python log_file_analyzer.py app.log --severity ERROR
    python log_file_analyzer.py app.log --since "2024-01-01"
    python log_file_analyzer.py app.log --stats
    python log_file_analyzer.py app.log --json
    python log_file_analyzer.py app.log *.log --aggregate
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional


# Predefined patterns for common log formats
PATTERNS = {
    "python": re.compile(r"(?P<ts>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[,\.]\d+)\s+-\s+(?P<level>[A-Z]+)\s+-\s+(?P<msg>.*)"),
    "apache": re.compile(r'(?P<ip>[\d.]+)\s+\S+\s+\S+\s+\[(?P<ts>[^\]]+)\]\s+"(?P<req>[^"]+)"\s+(?P<code>\d+)\s+(?P<size>\d+)'),
    "nginx": re.compile(r'(?P<ip>[\d.]+)\s+-\s+\S+\s+\[(?P<ts>[^\]]+)\]\s+"(?P<req>[^"]+)"\s+(?P<code>\d+)\s+(?P<size>\d+)'),
    "syslog": re.compile(r"(?P<ts>\w{3}\s+\d+\s+\d{2}:\d{2}:\d{2})\s+(?P<host>\S+)\s+(?P<msg>.*)"),
    "json": re.compile(r"^\s*\{.*\}\s*$"),
}


def _parse_json_line(line: str) -> Optional[dict]:
    try:
        obj = json.loads(line)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    return None


def _try_parse_timestamp(val: str) -> Optional[datetime]:
    formats = [
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%b/%Y:%H:%M:%S",
        "%b %d %H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(val[: len(fmt)], fmt)
        except ValueError:
            pass
    return None


SEVERITY_RE = re.compile(r"\b(TRACE|DEBUG|INFO|NOTICE|WARNING|WARN|ERROR|ERR|CRITICAL|CRIT|FATAL|ALERT|EMERGENCY)\b", re.IGNORECASE)


def _detect_severity(line: str) -> str:
    match = SEVERITY_RE.search(line)
    return match.group(1).upper() if match else "INFO"


def _detect_format(sample: list[str]) -> str:
    for line in sample:
        if _parse_json_line(line):
            return "json"
    for name, pat in PATTERNS.items():
        if pat.match(line):
            return name
    return "python"


def _parse_line(line: str, fmt: str) -> Optional[dict]:
    if fmt == "json":
        obj = _parse_json_line(line)
        if obj:
            return {"msg": json.dumps(obj), "level": obj.get("level", "INFO"), "ts": obj.get("timestamp")}
    elif fmt == "python":
        m = PATTERNS["python"].match(line)
        if m:
            return {"msg": m.group("msg"), "level": m.group("level"), "ts": m.group("ts")}
    elif fmt in ("apache", "nginx"):
        m = PATTERNS[fmt].match(line)
        if m:
            return {"msg": m.group("req"), "level": m.group("code"), "ts": m.group("ts")}
    elif fmt == "syslog":
        m = PATTERNS["syslog"].match(line)
        if m:
            return {"msg": m.group("msg"), "level": _detect_severity(m.group("msg")), "ts": m.group("ts")}
    return {"msg": line, "level": _detect_severity(line), "ts": None}


def parse_log(path: Path, since: Optional[str] = None, until: Optional[str] = None, levels: Optional[list[str]] = None) -> list[dict]:
    content = path.read_text(encoding="utf-8", errors="ignore")
    lines = [l for l in content.splitlines() if l.strip()]

    fmt = _detect_format(lines[: min(20, len(lines))])

    since_dt = _try_parse_timestamp(since) if since else None
    until_dt = _try_parse_timestamp(until) if until else None

    results: list[dict] = []
    for raw in lines:
        entry = _parse_line(raw, fmt)
        if entry["ts"]:
            entry["ts_parsed"] = _try_parse_timestamp(entry["ts"])
            if since_dt and entry["ts_parsed"] and entry["ts_parsed"] < since_dt:
                continue
            if until_dt and entry["ts_parsed"] and entry["ts_parsed"] > until_dt:
                continue
        if levels and entry["level"].upper() not in levels:
            continue
        entry["raw"] = raw
        results.append(entry)

    return results


def stats(entries: list[dict]) -> dict:
    total = len(entries)
    severity_counts = Counter(e["level"].upper() for e in entries)
    error_lines = [e["raw"] for e in entries if e["level"].upper() in ("ERROR", "FATAL", "CRITICAL", "CRIT", "ALERT")]
    top_errors = Counter(error_lines).most_common(20)

    return {
        "total": total,
        "by_severity": dict(severity_counts),
        "error_count": len(error_lines),
        "top_errors": top_errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Log File Analyzer")
    parser.add_argument("files", nargs="+", help="Log files")
    parser.add_argument("--errors", action="store_true", help="Show error lines only")
    parser.add_argument("--severity", help="Filter by severity level(s), comma-separated")
    parser.add_argument("--since", help="Filter from timestamp")
    parser.add_argument("--until", help="Filter until timestamp")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--aggregate", action="store_true", help="Aggregate across all files")
    args = parser.parse_args()

    all_entries: list[dict] = []
    levels = [l.upper() for l in args.severity.split(",")] if args.severity else None

    for f in args.files:
        path = Path(f).resolve()
        if not path.exists():
            print(f"Warning: '{f}' not found", file=sys.stderr)
            continue
        entries = parse_log(path, since=args.since, until=args.until, levels=levels)
        if args.aggregate:
            all_entries.extend(entries)
        else:
            all_entries = entries

    if args.stats:
        st = stats(all_entries)
        if args.json:
            print(json.dumps(st, indent=2))
        else:
            print(f"Total lines : {st['total']}")
            print(f"Errors   : {st['error_count']}")
            print("Severity breakdown:")
            for lvl, cnt in sorted(st["by_severity"].items(), key=lambda x: x[1], reverse=True):
                print(f"  {lvl}: {cnt}")
            if st["top_errors"][:5]:
                print("\nMost frequent errors:")
                for msg, cnt in st["top_errors"][:5]:
                    print(f"  [{cnt}x] {msg[:120]}")
        return

    if args.errors:
        for e in all_entries:
            if e["level"].upper() in ("ERROR", "FATAL", "CRITICAL", "CRIT", "ALERT"):
                print(e["raw"])
        return

    for e in all_entries[:100]:
        ts = e["ts"] or ""
        print(f"[{ts}] [{e['level']}] {e['msg']}")


if __name__ == "__main__":
    main()