#!/usr/bin/env python3
"""
batch_processor.py

A robust utility for parallel processing (ThreadPool or ProcessPool).
Features progress bars, exception handling, and ordered results.

Usage:
    from batch_processor import batch_process

    results = batch_process(range(100), expensive_func, workers=4)
"""

from __future__ import annotations

import argparse
import concurrent.futures
import logging
import multiprocessing
import os
from typing import Callable, Iterable, List, TypeVar, Optional

from tqdm import tqdm

T = TypeVar("T")
R = TypeVar("R")

log = logging.getLogger(__name__)

def batch_process(
    items: Iterable[T],
    fn: Callable[[T], R],
    *,
    workers: int = 1,
    executor_type: str = "thread",  # 'thread' or 'process'
    chunk_size: int = 1,
    desc: str = "Processing",
    on_error: str = "raise",  # 'raise' or 'skip'
) -> List[R]:
    """
    Apply ``fn`` to every element of ``items`` in parallel.

    Parameters
    ----------
    items : Iterable
        Input data.
    fn : Callable
        Function to apply.
    workers : int
        Number of workers. 1 for sequential, 0 for CPU count.
    executor_type : str
        'thread' (default) for I/O bound tasks.
        'process' for CPU bound tasks (avoids GIL).
    chunk_size : int
        Number of items per task (useful for ProcessPool to reduce IPC overhead).
    on_error : str
        'raise' (default) to stop on first exception.
        'skip' to replace failed items with None and continue.
    """
    items_list = list(items)
    if not items_list:
        return []

    # Sequential fallback
    if workers == 1:
        log.debug("Running sequentially")
        results = []
        for item in tqdm(items_list, desc=desc):
            try:
                results.append(fn(item))
            except Exception as e:
                if on_error == "raise":
                    raise
                log.warning(f"Error processing item: {e}")
                results.append(None)
        return results

    # Determine worker count
    if workers <= 0:
        workers = os.cpu_count() or 1

    # Choose Executor
    if executor_type == "process":
        Executor = concurrent.futures.ProcessPoolExecutor
        log.debug(f"Running with {workers} processes (chunk_size={chunk_size})")
    else:
        Executor = concurrent.futures.ThreadPoolExecutor
        log.debug(f"Running with {workers} threads")

    results: List[Optional[R]] = [None] * len(items_list)

    # Wrapper to handle exceptions inside the worker
    def _worker(idx_item: tuple) -> tuple:
        idx, item = idx_item
        try:
            return idx, fn(item)
        except Exception as e:
            if on_error == "raise":
                raise
            log.warning(f"Error at index {idx}: {e}")
            return idx, None

    with Executor(max_workers=workers) as executor:
        # Map indices to items to track ordering
        indexed_items = enumerate(items_list)
        
        # ProcessPoolExecutor benefits from chunking; ThreadPool does not use chunksize param in submit
        # We manually create tasks
        futures = {
            executor.submit(_worker, (idx, item)): idx
            for idx, item in indexed_items
        }

        for f in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc=desc):
            try:
                idx, result = f.result()
                results[idx] = result
            except Exception as e:
                if on_error == "raise":
                    raise
                # If we reach here, _worker returned None or failed differently
                # But _worker catches it if on_error='skip'.
                pass

    return results


def _demo_fn(x: int) -> int:
    """Demo function: squares the integer."""
    return x * x


def main() -> None:
    parser = argparse.ArgumentParser(description="Parallel Batch Processor Demo")
    parser.add_argument("-n", "--max", type=int, default=1000, help="Items to process")
    parser.add_argument("-w", "--workers", type=int, default=4, help="Workers (0 for CPU count)")
    parser.add_argument("-t", "--type", choices=["thread", "process"], default="thread", help="Executor type")
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(asctime)s - %(message)s")

    res = batch_process(
        range(1, args.max + 1),
        _demo_fn,
        workers=args.workers,
        executor_type=args.type,
        desc="Squaring"
    )
    log.info(f"Finished. Sample results: {res[:5]}")


if __name__ == "__main__":
    main()
