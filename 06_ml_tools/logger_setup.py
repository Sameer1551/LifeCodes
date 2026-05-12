#!/usr/bin/env python3
"""
logger_setup.py

A robust, production-ready logging toolkit for developers.

Features:
* `setup_logging()` – One-line setup for console + file logging with rotation.
* `get_logger()` – Standard logger retrieval.
* `@error_tracker` – Decorator to catch exceptions, log args, and re-raise.
* `@performance_timer` – Context/Decorator to log Wall Time & CPU Time.
* `@debug_params` – Decorator to log inputs/outputs at DEBUG level.

Dependencies:
    pip install python-json-logger  # Optional, for JSON output
"""

from __future__ import annotations

import argparse
import functools
import logging
import logging.handlers
import os
import sys
import time
import traceback
from contextlib import ContextDecorator
from pathlib import Path
from typing import Any, Callable, Dict, Optional

# ----------------------------------------------------------------------
# Optional JSON formatter
# ----------------------------------------------------------------------
try:
    from pythonjsonlogger import jsonlogger
except ImportError:
    jsonlogger = None  # type: ignore

# ----------------------------------------------------------------------
# Defaults
# ----------------------------------------------------------------------
DEFAULT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    json_format: bool = False,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
) -> logging.Logger:
    """
    Configure the root logger with console output and optional rotating file output.
    This should be called ONCE at application startup.

    Parameters
    ----------
    level
        Logging level (e.g., logging.INFO, logging.DEBUG).
    log_file
        Optional path to a log file. If provided, enables rotating file logging.
    json_format
        If True, output JSON logs (requires python-json-logger).
    max_bytes
        Max size of each log file before rotation (default 10MB).
    backup_count
        Number of backup files to keep (default 5).
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers to avoid duplicates in notebooks or reruns
    if root_logger.handlers:
        root_logger.handlers.clear()

    # 1. Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    if json_format and jsonlogger:
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt=DEFAULT_DATEFMT,
        )
    else:
        formatter = logging.Formatter(DEFAULT_FORMAT, datefmt=DEFAULT_DATEFMT)

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 2. File Handler (Rotating)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        logging.info(f"Logging to file: {log_file}")

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Return a logger instance. 
    NOTE: Call `setup_logging()` first to configure the root logger.
    """
    return logging.getLogger(name)


# ----------------------------------------------------------------------
# 1️⃣  ERROR TRACKER (Enhanced)
# ----------------------------------------------------------------------
def error_tracker(logger: Optional[logging.Logger] = None) -> Callable:
    """
    Decorator that catches exceptions, logs the full traceback AND the
    function arguments (args/kwargs), then re-raises.
    """
    if logger is None:
        logger = get_logger(__name__)

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                # Capture arguments for better debugging
                arg_str = f"args={args}, kwargs={kwargs}"
                tb = traceback.format_exc()
                logger.error(
                    f"Exception in {func.__name__}({arg_str}):\n{tb}"
                )
                raise

        return wrapper
    return decorator


# ----------------------------------------------------------------------
# 2️⃣  PERFORMANCE TIMER (Enhanced)
# ----------------------------------------------------------------------
class performance_timer(ContextDecorator):
    """
    Context manager and decorator that measures Wall Time and CPU Time.
    
    Example:
        with performance_timer("my_block"):
            # do work
    """
    def __init__(self, name: str = "block", logger: Optional[logging.Logger] = None):
        self.name = name
        self.logger = logger or get_logger(__name__)

    def __enter__(self):
        self._start_wall = time.perf_counter()
        self._start_cpu = time.process_time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        wall_elapsed = time.perf_counter() - self._start_wall
        cpu_elapsed = time.process_time() - self._start_cpu
        
        msg = (
            f"Timer [{self.name}] - "
            f"Wall: {wall_elapsed:.4f}s, CPU: {cpu_elapsed:.4f}s"
        )
        self.logger.info(msg)
        return False


# ----------------------------------------------------------------------
# 3️⃣  DEBUG PARAMS
# ----------------------------------------------------------------------
def debug_params(logger: Optional[logging.Logger] = None) -> Callable:
    """
    Decorator that logs function call details (inputs) and return value.
    Useful for tracing execution flow during debugging.
    """
    if logger is None:
        logger = get_logger(__name__)

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger.debug(f"Calling {func.__name__} | args={args} | kwargs={kwargs}")
            result = func(*args, **kwargs)
            # Be careful logging large objects
            logger.debug(f"Finished {func.__name__} | return={result}")
            return result
        return wrapper
    return decorator


# ----------------------------------------------------------------------
# CLI DEMO
# ----------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Demo utilities for logging, error tracking and timers.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("demo", help="Show a quick log demo")

    p_timer = sub.add_parser("timer-demo", help="Demo of the performance_timer")
    p_timer.add_argument("--name", default="demo_block", help="Timer name")
    p_timer.add_argument("--sleep", type=float, default=0.75, help="Seconds to sleep")

    p_file = sub.add_parser("file-demo", help="Demo logging to a file")
    p_file.add_argument("--output", default="app.log", help="Log file path")

    sub.add_parser("error-demo", help="Demo of the error_tracker decorator")

    return parser


def _dispatch(args: argparse.Namespace) -> None:
    # Initialize logging for the demo
    if args.cmd == "file-demo":
        print(f"Logging to {args.output}...")
        setup_logging(level=logging.DEBUG, log_file=args.output)
    else:
        setup_logging(level=logging.DEBUG)

    log = get_logger("demo_app")

    if args.cmd == "demo":
        log.info("This is an INFO message")
        log.warning("This is a WARNING")
        log.error("This is an ERROR")
        log.debug("Debug output – visible because level is DEBUG")

        if jsonlogger:
            print("\n--- JSON Output Demo ---")
            # Switch to JSON for this specific logger
            setup_logging(json_format=True)
            json_log = get_logger("json_demo")
            json_log.info("A JSON-formatted log line", extra={"user_id": 123})
        else:
            log.info("Install 'python-json-logger' for JSON output")

    elif args.cmd == "timer-demo":
        with performance_timer(name=args.name, logger=log):
            # Simulate work
            time.sleep(args.sleep)

    elif args.cmd == "file-demo":
        log.info("This message is stored in a rotating file.")
        log.debug("Debug details also go to the file.")
        print(f"Check content in {args.output}")

    elif args.cmd == "error-demo":
        @error_tracker(log)
        def fails(arg1, arg2="value"):
            # Intentional error to demonstrate argument logging
            raise RuntimeError("Simulated failure for demo")

        try:
            fails("input_data")
        except RuntimeError:
            log.info("Caught the re-raised exception – demo complete")


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    try:
        _dispatch(args)
    except Exception as exc:
        print(f"Fatal error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
