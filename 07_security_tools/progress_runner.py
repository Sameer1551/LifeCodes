#!/usr/bin/env python3
"""
progress_runner.py

A robust wrapper for tqdm progress bars, useful for loops and generators.
"""

import argparse
import logging
import time
from typing import Iterable, TypeVar, Callable

from tqdm import tqdm

T = TypeVar("T")
log = logging.getLogger(__name__)

def progress(
    iterable: Iterable[T],
    desc: str = "Processing",
    total: int = None,
    unit: str = "it",
) -> Iterable[T]:
    """
    Wrap an iterable with a tqdm progress bar.
    
    Parameters
    ----------
    iterable : Iterable
        The data stream.
    desc : str
        Description prefix.
    total : int, optional
        Total count if known (speeds up bars for generators).
    unit : str
        Unit name (e.g. 'files', 'rows').
    """
    return tqdm(iterable, desc=desc, total=total, unit=unit, dynamic_ncols=True)

def run_with_timer(
    iterable: Iterable[T],
    fn: Callable[[T], None],
    total: int = None
) -> float:
    """
    Apply `fn` to every item in `iterable` with a progress bar.
    Returns total elapsed time.
    """
    start = time.time()
    for item in progress(iterable, total=total):
        fn(item)
    return time.time() - start

def _demo():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    
    def process_item(x):
        time.sleep(0.01) # Simulate work
        return x * 2

    items = range(500)
    
    log.info("Starting processing...")
    elapsed = run_with_timer(items, process_item, total=500)
    
    log.info(f"Finished in {elapsed:.2f}s")

def main():
    parser = argparse.ArgumentParser(description="Progress Runner Demo")
    parser.add_argument("--total", type=int, default=100, help="Number of items")
    parser.add_argument("--delay", type=float, default=0.01, help="Simulated delay per item")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    
    def task(x):
        time.sleep(args.delay)
    
    run_with_timer(range(args.total), task, total=args.total)

if __name__ == "__main__":
    main()
