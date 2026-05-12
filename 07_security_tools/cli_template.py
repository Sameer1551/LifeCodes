#!/usr/bin/env python3
"""
cli_template.py

A professional CLI template with colored logging, subcommands, and common flags.
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Dict, Callable

# ----------------------------------------------------------------------
# Colored Logging Setup
# ----------------------------------------------------------------------
class ColorFormatter(logging.Formatter):
    """Adds color to log levelnames based on severity."""
    grey = "\x1b[38;21m"
    green = "\x1b[32;21m"
    yellow = "\x1b[33;21m"
    red = "\x1b[31;21m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    fmt = "%(asctime)s | %(levelname)s | %(message)s"

    FORMATS = {
        logging.DEBUG: grey + fmt + reset,
        logging.INFO: green + fmt + reset,
        logging.WARNING: yellow + fmt + reset,
        logging.ERROR: red + fmt + reset,
        logging.CRITICAL: bold_red + fmt + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, self.fmt)
        formatter = logging.Formatter(log_fmt, datefmt="%H:%M:%S")
        return formatter.format(record)

log = logging.getLogger("cli")
handler = logging.StreamHandler()
handler.setFormatter(ColorFormatter())
log.addHandler(handler)
log.setLevel(logging.INFO)

# ----------------------------------------------------------------------
# Command Actions
# ----------------------------------------------------------------------
def cmd_demo(ns: argparse.Namespace) -> None:
    """Example command implementation."""
    if ns.dry_run:
        log.warning("DRY-RUN: Would process demo")
        return
    
    log.info(f"Running demo with foo={ns.foo} count={ns.count}")
    for i in range(ns.count):
        log.debug(f"Processing item {i+1}")
        print(f"Output: {ns.foo} - {i+1}")

def cmd_hello(ns: argparse.Namespace) -> None:
    """Another example command."""
    log.info("Hello World!")

# Registry of commands
COMMANDS: Dict[str, Callable] = {
    "demo": cmd_demo,
    "hello": cmd_hello,
}

# ----------------------------------------------------------------------
# Argument Parser Setup
# ----------------------------------------------------------------------
def add_common_args(parser: argparse.ArgumentParser) -> None:
    """Attach common flags to a sub-parser."""
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logs")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without side-effects")

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="CLI Template Tool", 
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Demo command
    p_demo = subparsers.add_parser("demo", help="Run the demo")
    p_demo.add_argument("--foo", default="bar", help="Sample string")
    p_demo.add_argument("--count", type=int, default=1, help="Repetitions")
    add_common_args(p_demo)

    # Hello command
    p_hello = subparsers.add_parser("hello", help="Say hello")
    add_common_args(p_hello)

    return parser

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Update log level
    if args.verbose:
        log.setLevel(logging.DEBUG)

    # Dispatch
    func = COMMANDS[args.command]
    try:
        func(args)
    except Exception as e:
        log.exception(f"Error running {args.command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
