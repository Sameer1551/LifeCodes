#!/usr/bin/env python3
"""
system_info_reporter.py

Universal system information reporter.
Cross-platform (Windows, Linux, macOS, BSD).
Reports OS, CPU, RAM, disk, network, and uptime.
Language-agnostic, platform-agnostic.

Usage:
    python system_info_reporter.py
    python system_info_reporter.py --format json
    python system_info_reporter.py --format html --out report.html
    python system_info_reporter.py --short
    python system_info_reporter.py --all
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


class CommandRunner:
    """Cross-platform command runner."""
    
    @staticmethod
    def run(cmd: List[str], timeout: int = 10) -> str:
        """Run command and return output."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return ""
    
    @staticmethod
    def run_powershell(command: str, timeout: int = 10) -> str:
        """Run PowerShell command (Windows)."""
        try:
            result = subprocess.run(
                ["powershell", "-Command", command],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.stdout.strip()
        except Exception:
            return ""
    
    @staticmethod
    def run_shell(command: str, timeout: int = 10) -> str:
        """Run shell command (Unix-like)."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.stdout.strip()
        except Exception:
            return ""


class OSInfo:
    """Operating system information."""
    
    @staticmethod
    def get() -> Dict[str, str]:
        """Get OS information."""
        return {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "hostname": platform.node(),
            "python_version": sys.version.split()[0],
        }


class CPUInfo:
    """CPU information."""
    
    @staticmethod
    def get() -> Dict[str, Any]:
        """Get CPU information."""
        info = {
            "count_logical": os.cpu_count() or 1,
            "count_physical": 1,
            "architecture": platform.machine(),
            "processor": platform.processor(),
        }
        
        # Try to get physical core count
        if platform.system() == "Linux":
            try:
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if line.startswith("cpu cores"):
                            info["count_physical"] = int(line.split(":")[1].strip())
                            break
            except Exception:
                pass
        elif platform.system() == "Darwin":
            result = CommandRunner.run_shell("sysctl -n hw.physicalcpu")
            if result:
                info["count_physical"] = int(result)
        elif platform.system() == "Windows":
            result = CommandRunner.run_powershell("(Get-CimInstance Win32_Processor).NumberOfCores")
            if result:
                info["count_physical"] = int(result)
        
        return info


class MemoryInfo:
    """Memory information."""
    
    @staticmethod
    def get() -> Dict[str, Any]:
        """Get memory information."""
        info = {
            "total_gb": 0,
            "available_gb": 0,
            "used_gb": 0,
            "percent": 0,
        }
        
        if platform.system() == "Linux":
            try:
                with open("/proc/meminfo", "r") as f:
                    meminfo = {}
                    for line in f:
                        parts = line.split(":")
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value = parts[1].strip().split()[0]
                            meminfo[key] = int(value)
                
                    total_kb = meminfo.get("MemTotal", 0)
                    available_kb = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
                    used_kb = total_kb - available_kb
                
                info["total_gb"] = round(total_kb / (1024 * 1024), 2)
                info["available_gb"] = round(available_kb / (1024 * 1024), 2)
                info["used_gb"] = round(used_kb / (1024 * 1024), 2)
                info["percent"] = round(used_kb / total_kb * 100, 1) if total_kb else 0
            except Exception:
                pass
        
        elif platform.system() == "Darwin":
            try:
                result = CommandRunner.run_shell("sysctl -n hw.memsize")
                if result:
                    total_bytes = int(result)
                    result = CommandRunner.run_shell("vm_stat | grep 'Pages free' | awk '{print $3}'")
                    if result:
                        free_pages = int(result.replace(".", ""))
                        free_bytes = free_pages * 4096
                        used_bytes = total_bytes - free_bytes
                        
                        info["total_gb"] = round(total_bytes / (1024**3), 2)
                        info["available_gb"] = round(free_bytes / (1024**3), 2)
                        info["used_gb"] = round(used_bytes / (1024**3), 2)
                        info["percent"] = round(used_bytes / total_bytes * 100, 1)
            except Exception:
                pass
        
        elif platform.system() == "Windows":
            try:
                result = CommandRunner.run_powershell(
                    "(Get-CimInstance Win32_OperatingSystem) | "
                    "Select-Object TotalVisibleMemorySize,FreePhysicalMemory | "
                    "ConvertTo-Json -Compress"
                )
                if result:
                    data = json.loads(result)
                    total = int(data.get("TotalVisibleMemorySize", 0)) * 1024
                    free = int(data.get("FreePhysicalMemory", 0)) * 1024
                    used = total - free
                    
                    info["total_gb"] = round(total / (1024**3), 2)
                    info["available_gb"] = round(free / (1024**3), 2)
                    info["used_gb"] = round(used / (1024**3), 2)
                    info["percent"] = round(used / total * 100, 1) if total else 0
            except Exception:
                pass
        
        return info


class DiskInfo:
    """Disk information."""
    
    @staticmethod
    def get() -> List[Dict[str, Any]]:
        """Get disk information."""
        disks = []
        
        if platform.system() == "Linux":
            try:
                result = CommandRunner.run_shell("df -T | grep -v tmpfs | grep -v devtmpfs")
                for line in result.split("\n")[1:]:
                    parts = line.split()
                    if len(parts) >= 6:
                        mount = parts[6]
                        total = int(parts[2])
                        used = int(parts[3])
                        free = int(parts[4])
                        
                        disks.append({
                            "mount": mount,
                            "total_gb": round(total / (1024**3), 2),
                            "used_gb": round(used / (1024**3), 2),
                            "free_gb": round(free / (1024**3), 2),
                            "percent": round(used / total * 100, 1) if total else 0,
                        })
            except Exception:
                pass
        
        elif platform.system() == "Darwin":
            try:
                result = CommandRunner.run_shell("df -H | grep -v tmpfs | grep -v devfs")
                for line in result.split("\n")[1:]:
                    parts = line.split()
                    if len(parts) >= 6:
                        mount = parts[-1]
                        total = DiskInfo._parse_size(parts[1])
                        used = DiskInfo._parse_size(parts[2])
                        free = DiskInfo._parse_size(parts[3])
                        
                        disks.append({
                            "mount": mount,
                            "total_gb": round(total, 2),
                            "used_gb": round(used, 2),
                            "free_gb": round(free, 2),
                            "percent": round(used / total * 100, 1) if total else 0,
                        })
            except Exception:
                pass
        
        elif platform.system() == "Windows":
            try:
                result = CommandRunner.run_powershell(
                    "Get-CimInstance Win32_LogicalDisk | "
                    "Select-Object DeviceID,Size,FreeSpace | "
                    "ConvertTo-Json"
                )
                if result:
                    data = json.loads(result)
                    if not isinstance(data, list):
                        data = [data]
                    
                    for d in data:
                        if d.get("Size"):
                            total = int(d["Size"])
                            free = int(d["FreeSpace"])
                            used = total - free
                            
                            disks.append({
                                "mount": d["DeviceID"],
                                "total_gb": round(total / (1024**3), 2),
                                "used_gb": round(used / (1024**3), 2),
                                "free_gb": round(free / (1024**3), 2),
                                "percent": round(used / total * 100, 1),
                            })
            except Exception:
                pass
        
        return disks
    
    @staticmethod
    def _parse_size(size_str: str) -> float:
        """Parse size string (e.g., '500G', '100M') to GB."""
        size_str = size_str.upper()
        multipliers = {
            "T": 1024,
            "G": 1,
            "M": 1 / 1024,
            "K": 1 / (1024**2),
            "B": 1 / (1024**3),
        }
        
        for suffix, mult in multipliers.items():
            if size_str.endswith(suffix):
                value = float(size_str[:-1])
                return value * mult
        
        return float(size_str)


class NetworkInfo:
    """Network information."""
    
    @staticmethod
    def get() -> Dict[str, Any]:
        """Get network information."""
        info = {
            "hostname": platform.node(),
            "ip_address": "",
            "mac_address": "",
        }
        
        try:
            info["hostname"] = platform.node()
        except Exception:
            pass
        
        # Get IP address
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            info["ip_address"] = s.getsockname()[0]
            s.close()
        except Exception:
            pass
        
        # Get MAC address
        try:
            import uuid
            info["mac_address"] = ":".join(f"{x:02x}" for x in uuid.getnode().to_bytes(6, "big"))
        except Exception:
            pass
        
        return info


class UptimeInfo:
    """System uptime information."""
    
    @staticmethod
    def get() -> Dict[str, Any]:
        """Get system uptime."""
        info = {
            "uptime_seconds": 0,
            "uptime_human": "",
            "boot_time": "",
        }
        
        if platform.system() == "Linux":
            try:
                with open("/proc/uptime", "r") as f:
                    uptime_seconds = float(f.read().split()[0])
                    info["uptime_seconds"] = int(uptime_seconds)
                    info["uptime_human"] = UptimeInfo._format_uptime(uptime_seconds)
                    info["boot_time"] = (datetime.now() - timedelta(seconds=uptime_seconds)).isoformat()
            except Exception:
                pass
        
        elif platform.system() == "Darwin":
            try:
                result = CommandRunner.run_shell("sysctl -n kern.boottime")
                if result:
                    boot_time = datetime.fromtimestamp(int(result.split("{")[1].split(",")[0]))
                    uptime_seconds = (datetime.now() - boot_time).total_seconds()
                    info["uptime_seconds"] = int(uptime_seconds)
                    info["uptime_human"] = UptimeInfo._format_uptime(uptime_seconds)
                    info["boot_time"] = boot_time.isoformat()
            except Exception:
                pass
        
        elif platform.system() == "Windows":
            try:
                result = CommandRunner.run_powershell(
                    "(Get-CimInstance Win32_OperatingSystem).LastBootUpTime"
                )
                if result:
                    boot_time = datetime.fromisoformat(result)
                    uptime_seconds = (datetime.now() - boot_time).total_seconds()
                    info["uptime_seconds"] = int(uptime_seconds)
                    info["uptime_human"] = UptimeInfo._format_uptime(uptime_seconds)
                    info["boot_time"] = boot_time.isoformat()
            except Exception:
                pass
        
        return info
    
    @staticmethod
    def _format_uptime(seconds: float) -> str:
        """Format uptime in human-readable form."""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        
        return " ".join(parts) if parts else "0m"


class SystemReporter:
    """Main system reporter."""
    
    def __init__(self, include_all: bool = False):
        self.include_all = include_all
    
    def get_all(self) -> Dict[str, Any]:
        """Get all system information."""
        info = {
            "timestamp": datetime.now().isoformat(),
            "os": OSInfo.get(),
            "cpu": CPUInfo.get(),
            "memory": MemoryInfo.get(),
            "disk": DiskInfo.get(),
        }
        
        if self.include_all:
            info["network"] = NetworkInfo.get()
            info["uptime"] = UptimeInfo.get()
        
        return info
    
    def format_text(self, info: Dict[str, Any], short: bool = False) -> str:
        """Format as text."""
        if short:
            cpu = info["cpu"]["count_logical"]
            mem = info["memory"]
            return (
                f"{info['os']['system']} | {cpu} cores | "
                f"RAM {mem.get('used_gb','?')}/{mem.get('total_gb','?')} GB | "
                f"{mem.get('percent','?')}%"
            )
        
        lines = ["=== System Info ==="]
        lines.append(f"Time   : {info['timestamp']}")
        lines.append(f"Host   : {info['os']['hostname']}")
        lines.append(f"OS     : {info['os']['system']} {info['os']['release']} ({info['os']['machine']})")
        lines.append(f"Python : {info['os']['python_version']}")
        
        cpu = info["cpu"]
        lines.append(f"CPU    : {cpu['count_logical']} logical cores, {cpu['count_physical']} physical ({cpu['architecture']})")
        
        mem = info["memory"]
        if mem.get("total_gb"):
            lines.append(f"RAM    : {mem['total_gb']} GB total, {mem['used_gb']} GB used ({mem['percent']}%)")
        
        for disk in info["disk"][:3]:
            lines.append(f"Disk {disk['mount']}: {disk['total_gb']} GB ({disk['percent']}% used)")
        
        if self.include_all:
            if "network" in info:
                net = info["network"]
                lines.append(f"Network: {net['hostname']} | IP: {net.get('ip_address', 'N/A')}")
            if "uptime" in info:
                up = info["uptime"]
                lines.append(f"Uptime : {up.get('uptime_human', 'N/A')} (booted: {up.get('boot_time', 'N/A')})")
        
        return "\n".join(lines)
    
    def format_json(self, info: Dict[str, Any]) -> str:
        """Format as JSON."""
        return json.dumps(info, indent=2, default=str)
    
    def format_html(self, info: Dict[str, Any]) -> str:
        """Format as HTML."""
        lines = ["<html><head><title>System Report</title></head><body>"]
        lines.append("<h1>System Report</h1>")
        lines.append("<table border='1'>")
        
        for key, value in info.items():
            if isinstance(value, dict):
                lines.append(f"<tr><td colspan='2'><strong>{key.upper()}</strong></td></tr>")
                for k, v in value.items():
                    lines.append(f"<tr><td>{k}</td><td>{v}</td></tr>")
            elif isinstance(value, list):
                lines.append(f"<tr><td colspan='2'><strong>{key.upper()}</strong></td></tr>")
                for item in value:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            lines.append(f"<tr><td>{k}</td><td>{v}</td></tr>")
            else:
                lines.append(f"<tr><td>{key}</td><td>{value}</td></tr>")
        
        lines.append("</table></body></html>")
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Universal System Info Reporter",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--format", choices=["text", "json", "html"], default="text", help="Output format")
    parser.add_argument("--out", help="Output file")
    parser.add_argument("--short", action="store_true", help="Short output")
    parser.add_argument("--all", action="store_true", help="Include all information (network, uptime)")
    args = parser.parse_args()

    reporter = SystemReporter(include_all=args.all)
    info = reporter.get_all()

    if args.format == "json":
        output = reporter.format_json(info)
    elif args.format == "html":
        output = reporter.format_html(info)
    else:
        output = reporter.format_text(info, short=args.short)

    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"Written to {args.out}")
    else:
        print(output)


if __name__ == "__main__":
    main()
