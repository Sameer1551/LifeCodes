#!/usr/bin/env python3
"""
system_utils.py

A robust toolkit for OS-level diagnostics and automation:

* CPU / RAM / Disk Monitor (live watching supported)
* Network speed test (download / upload / ping)
* Process killer (by PID or name, supports SIGTERM/SIGKILL)
* TCP Port Scanner (Multithreaded for speed)

Dependencies
------------
* psutil          - system metrics (pip install psutil)
* speedtest-cli   - internet speed test (pip install speedtest-cli)

Usage:
    python system_utils.py cpu-ram --watch
    python system_utils.py disk-usage
    python system_utils.py speedtest
    python system_utils.py kill --name chrome --force
    python system_utils.py port-scan example.com --start 1 --end 1024 --threads 50
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import socket
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Optional

# ----------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Optional Imports
# ----------------------------------------------------------------------
try:
    import psutil
except ImportError:
    psutil = None

try:
    import speedtest
except ImportError:
    speedtest = None

try:
    from tqdm import tqdm
except ImportError:
    # Fallback iterator if tqdm is missing
    def tqdm(iterable, **kwargs):
        return iterable


# ----------------------------------------------------------------------
# Utilities
# ----------------------------------------------------------------------

def _check_psutil():
    if psutil is None:
        raise ImportError("Package 'psutil' is required for this command. Install with: pip install psutil")

def _check_speedtest():
    if speedtest is None:
        raise ImportError("Package 'speedtest-cli' is required for this command. Install with: pip install speedtest-cli")


# ----------------------------------------------------------------------
# 1️⃣  System Monitoring (CPU, RAM, Disk)
# ----------------------------------------------------------------------

def get_sys_info() -> Dict[str, float]:
    """Returns a dictionary with CPU, RAM, and Disk usage percentages."""
    _check_psutil()
    
    # CPU
    cpu_pct = psutil.cpu_percent(interval=0.5)
    
    # Memory
    vm = psutil.virtual_memory()
    ram_pct = vm.percent
    ram_used_gb = vm.used / (1024 ** 3)
    ram_total_gb = vm.total / (1024 ** 3)
    
    # Disk (Root partition)
    disk = psutil.disk_usage('/')
    disk_pct = disk.percent
    disk_used_gb = disk.used / (1024 ** 3)
    disk_total_gb = disk.total / (1024 ** 3)
    
    return {
        "cpu_pct": cpu_pct,
        "ram_pct": ram_pct, "ram_used_gb": ram_used_gb, "ram_total_gb": ram_total_gb,
        "disk_pct": disk_pct, "disk_used_gb": disk_used_gb, "disk_total_gb": disk_total_gb
    }

def print_sys_info():
    info = get_sys_info()
    print(f"{'Resource':<10} {'Usage %':<10} {'Used / Total':<20}")
    print("-" * 40)
    print(f"{'CPU':<10} {info['cpu_pct']:<10.1f} {'(N/A)':<20}")
    print(f"{'RAM':<10} {info['ram_pct']:<10.1f} {info['ram_used_gb']:.1f} / {info['ram_total_gb']:.1f} GB")
    print(f"{'Disk':<10} {info['disk_pct']:<10.1f} {info['disk_used_gb']:.1f} / {info['disk_total_gb']:.1f} GB")

def watch_system(interval: int = 2):
    """Continuously prints system stats until interrupted."""
    print("Starting live system monitor (Press Ctrl+C to stop)...\n")
    try:
        while True:
            info = get_sys_info()
            # Use carriage return to overwrite line for clean output
            sys.stdout.write(
                f"\rCPU: {info['cpu_pct']:5.1f}% | "
                f"RAM: {info['ram_pct']:5.1f}% ({info['ram_used_gb']:.1f}/{info['ram_total_gb']:.1f}GB) | "
                f"Disk: {info['disk_pct']:5.1f}% "
            )
            sys.stdout.flush()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")


# ----------------------------------------------------------------------
# 2️⃣  Network Speed Test
# ----------------------------------------------------------------------

def run_speedtest() -> dict:
    _check_speedtest()
    log.info("Running speed test (finding best server)...")
    st = speedtest.Speedtest()
    st.get_best_server()
    
    log.info("Testing download speed...")
    st.download()
    
    log.info("Testing upload speed...")
    st.upload()
    
    res = st.results.dict()
    return {
        "download_mbps": round(res["download"] / 1_000_000, 2),
        "upload_mbps": round(res["upload"] / 1_000_000, 2),
        "ping_ms": round(res["ping"], 2),
        "server": res["server"]["sponsor"],
        "client": res["client"]["ip"],
    }

def print_speedtest():
    results = run_speedtest()
    print("\n=== Speedtest Results ===")
    print(f"Client IP: {results['client']}")
    print(f"Server:    {results['server']}")
    print(f"Ping:      {results['ping_ms']} ms")
    print(f"Download:  {results['download_mbps']} Mbps")
    print(f"Upload:    {results['upload_mbps']} Mbps")


# ----------------------------------------------------------------------
# 3️⃣  Process Killer
# ----------------------------------------------------------------------

def kill_process(pid: Optional[int] = None, name: Optional[str] = None, force: bool = False) -> int:
    """
    Kill process by PID or Name.
    Returns number of processes killed.
    """
    _check_psutil()
    sig = psutil.signal.SIGKILL if force else psutil.signal.SIGTERM
    action = "Killed" if force else "Terminated"
    count = 0

    if pid:
        try:
            p = psutil.Process(pid)
            p.send_signal(sig)
            print(f"{action} PID {pid} ({p.name()})")
            count += 1
        except psutil.NoSuchProcess:
            log.error(f"PID {pid} does not exist.")
        except psutil.AccessDenied:
            log.error(f"Permission denied for PID {pid}. Try with sudo or --force.")
    
    elif name:
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if name.lower() in proc.info["name"].lower():
                    proc.send_signal(sig)
                    print(f"{action} PID {proc.pid} ({proc.info['name']})")
                    count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    
    return count


# ----------------------------------------------------------------------
# 4️⃣  Port Scanner (Multithreaded)
# ----------------------------------------------------------------------

def _probe_port(host: str, port: int, timeout: float) -> Optional[int]:
    """Returns port number if open, else None."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        try:
            sock.connect((host, port))
            return port
        except (socket.timeout, ConnectionRefusedError, OSError):
            return None

def scan_ports(host: str, start: int = 1, end: int = 1024, threads: int = 50, timeout: float = 0.5) -> List[int]:
    """
    Multithreaded port scanner.
    """
    if start < 1 or end > 65535 or start > end:
        raise ValueError("Port range must be 1-65535 and start <= end")

    open_ports = []
    ports = range(start, end + 1)
    
    # Use ThreadPoolExecutor for parallel scanning
    with ThreadPoolExecutor(max_workers=threads) as executor:
        # Map future to port
        future_to_port = {executor.submit(_probe_port, host, port, timeout): port for port in ports}
        
        # Progress bar
        for future in tqdm(as_completed(future_to_port), total=len(ports), desc=f"Scanning {host}"):
            result = future.result()
            if result:
                open_ports.append(result)

    return sorted(open_ports)

def print_port_scan(host: str, start: int, end: int, threads: int):
    open_ports = scan_ports(host, start, end, threads)
    print("\n" + "-" * 40)
    if open_ports:
        print(f"Open ports on {host} [{start}-{end}]:")
        for p in open_ports:
            print(f"  • {p}")
    else:
        print(f"No open ports found on {host} in range {start}-{end}.")


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="System-level utilities - CPU/RAM, Speedtest, Process Killer, Port Scanner.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # ---- Monitor ----
    p_mon = sub.add_parser("cpu-ram", help="Show CPU, RAM, and Disk usage")
    p_mon.add_argument("--watch", action="store_true", help="Continuously update stats")

    # ---- Disk Usage ----
    sub.add_parser("disk-usage", help="Show Disk usage (alias for cpu-ram currently)")

    # ---- Speedtest ----
    sub.add_parser("speedtest", help="Run an internet speed test")

    # ---- Kill ----
    p_kill = sub.add_parser("kill", help="Kill a process by PID or Name")
    group = p_kill.add_mutually_exclusive_group(required=True)
    group.add_argument("--pid", type=int, help="Process ID to terminate")
    group.add_argument("--name", type=str, help="Process name (case-insensitive substring)")
    p_kill.add_argument("--force", action="store_true", help="Force kill (SIGKILL) instead of terminate (SIGTERM)")

    # ---- Port Scan ----
    p_scan = sub.add_parser("port-scan", help="Multithreaded TCP port scanner")
    p_scan.add_argument("host", help="Hostname or IP address")
    p_scan.add_argument("--start", type=int, default=1, help="Start of port range")
    p_scan.add_argument("--end", type=int, default=1024, help="End of port range")
    p_scan.add_argument("--threads", type=int, default=50, help="Number of parallel threads")
    p_scan.add_argument("--timeout", type=float, default=0.5, help="Connection timeout per port")

    return parser

def _dispatch(args: argparse.Namespace) -> None:
    try:
        if args.cmd == "cpu-ram" or args.cmd == "disk-usage":
            if args.watch:
                watch_system()
            else:
                print_sys_info()

        elif args.cmd == "speedtest":
            print_speedtest()

        elif args.cmd == "kill":
            killed = kill_process(pid=args.pid, name=args.name, force=args.force)
            print(f"Total processes affected: {killed}")

        elif args.cmd == "port-scan":
            print_port_scan(args.host, args.start, args.end, args.threads)

        else:
            raise RuntimeError(f"Unsupported command: {args.cmd}")

    except ImportError as e:
        log.error(f"Missing dependency: {e}")
        log.error("Please install required packages (psutil, speedtest-cli) depending on the command.")
        sys.exit(1)
    except PermissionError:
        log.error("Permission denied. Try running with sudo/administrator privileges.")
        sys.exit(1)

def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    _dispatch(args)


if __name__ == "__main__":
    main()
