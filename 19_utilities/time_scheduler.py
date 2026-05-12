#!/usr/bin/env python3
"""
time_scheduler.py

Schedules and runs tasks at specified times (cron-like and one-shot).
Supports periodic intervals, daily/weekly schedules, and cron expressions.
Cross-platform. No external dependencies.

Usage:
    python time_scheduler.py --task "echo hello" --interval 60
    python time_scheduler.py --task "python script.py" --daily "09:00"
    python time_scheduler.py --task "backup.sh" --cron "0 2 * * *"
    python time_scheduler.py --task "report.py" --at "2026-01-01 10:00" --once
    python time_scheduler.py --watch tasks.csv
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


CRON_FIELDS = ["minute", "hour", "dom", "month", "dow"]


def _parse_cron_expr(expr: str) -> list[list[int]]:
    parts = expr.split()
    if len(parts) != 5:
        raise ValueError("Need 5 cron fields: minute hour dom month dow")
    result: list[list[int]] = []
    for field in parts:
        values: set[int] = set()
        for part in field.split(","):
            if part == "*":
                values.update(range(60 if len(result) == 0 else 24))
            elif "-" in part:
                start, end = part.split("-", 1)
                values.update(range(int(start), int(end) + 1))
            elif "/" in part:
                base, step = part.split("/", 1)
                max_val = 60 if len(result) == 0 else (24 if len(result) == 1 else 31 if len(result) == 2 else 12)
                values.update(range(0 if base == "*" else int(base), max_val + 1, int(step)))
            else:
                values.add(int(part))
        result.append(sorted(values))
    return result


def _cron_matches(expr: list[list[int]], now: datetime) -> bool:
    fields = [now.minute, now.hour, now.day, now.month, now.weekday()]
    for i, vals in enumerate(expr):
        if vals and fields[i] not in vals:
            return False
    return True


def _parse_time(val: str) -> tuple[int, int]:
    parts = val.split(":")
    return int(parts[0]), int(parts[1])


def run_task(command: str) -> int:
    if sys.platform == "win32":
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
    else:
        result = subprocess.run(shlex.split(command), capture_output=True, text=True)
    return result.returncode


def schedule_loop(tasks: list[dict]) -> None:
    running = True

    def _tick() -> None:
        while running:
            now = datetime.now()
            for task in tasks:
                if task.get("cron"):
                    if _cron_matches(task["cron_expr"], now):
                        run_task(task["command"])
                elif task.get("interval"):
                    if now - task.get("_last_run", now - timedelta(seconds=task["interval"] + 1)) >= timedelta(seconds=task["interval"]):
                        run_task(task["command"])
                        task["_last_run"] = now
                elif task.get("daily"):
                    h, m = _parse_time(task["daily"])
                    if now.hour == h and now.minute == m and now.second < 5:
                        run_task(task["command"])
            time.sleep(1)

    thread = threading.Thread(target=_tick, daemon=True)
    thread.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        running = False
        print("Scheduler stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Time Scheduler")
    parser.add_argument("--task", help="Command to run")
    parser.add_argument("--interval", type=int, help="Repeat every N seconds")
    parser.add_argument("--cron", help="Cron expression (min hour dom month dow)")
    parser.add_argument("--daily", help="Run daily at HH:MM")
    parser.add_argument("--at", help="Run once at YYYY-MM-DD HH:MM")
    parser.add_argument("--once", action="store_true", help="Run task once and exit")
    parser.add_argument("--watch", help="Load tasks from CSV file (command,schedule)")
    args = parser.parse_args()

    if args.watch:
        import csv as _csv
        tasks: list[dict] = []
        for row in _csv.reader(Path(args.watch).read_text(encoding="utf-8").splitlines()):
            if len(row) < 2:
                continue
            task: dict = {"command": row[0], "schedule": row[1]}
            if row[1].count(" ") == 4:
                task["cron"] = True
                task["cron_expr"] = _parse_cron_expr(row[1])
            elif ":" in row[1]:
                task["daily"] = row[1]
            else:
                task["interval"] = int(row[1])
            tasks.append(task)
        schedule_loop(tasks)
        return

    if not args.task:
        print("Error: --task required", file=sys.stderr)
        sys.exit(1)

    task: dict[str, object] = {"command": args.task}

    if args.at:
        dt = datetime.strptime(args.at, "%Y-%m-%d %H:%M")
        delay = (dt - datetime.now()).total_seconds()
        if delay <= 0:
            print("Time already passed")
            sys.exit(1)
        print(f"Waiting until {args.at} ({delay:.0f}s)...")
        time.sleep(delay)
        rc = run_task(args.task)
        print(f"Done, exit code: {rc}")
        return

    if args.cron:
        task["cron"] = True
        task["cron_expr"] = _parse_cron_expr(args.cron)
    elif args.interval:
        task["interval"] = args.interval
    elif args.daily:
        task["daily"] = args.daily

    if args.once:
        rc = run_task(args.task)
        sys.exit(rc)

    print(f"Scheduler started. Press Ctrl+C to stop.")
    schedule_loop([task])


if __name__ == "__main__":
    main()