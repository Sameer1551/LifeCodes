#!/usr/bin/env python3
"""
load_test.py
------------
Advanced load testing utility with ramp-up, validation, and detailed metrics.

Usage:
    python load_test.py --url http://localhost:8000/health --users 50 --requests 1000
    python load_test.py --url http://api/users --method POST --payload '{"id": 1}'
"""

import argparse
import json
import statistics
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

class LoadTestResult:
    def __init__(self):
        self.successes = 0
        self.failures = 0
        self.times_ms = []
        self.errors = set()
        self.status_codes = {}

def send_request(url, method, headers, payload, timeout, expect_json):
    """Sends a request and captures metrics."""
    start = time.time()
    result = {"success": False, "time_ms": 0, "status": None, "error": None}
    
    try:
        resp = requests.request(method, url, headers=headers, json=payload, timeout=timeout)
        elapsed = (time.time() - start) * 1000
        result["time_ms"] = elapsed
        result["status"] = resp.status_code

        # Validation
        if 200 <= resp.status_code < 300:
            if expect_json:
                try:
                    resp.json() # Validate JSON parsing
                    result["success"] = True
                except json.JSONDecodeError:
                    result["error"] = "Invalid JSON response"
            else:
                result["success"] = True
        else:
            result["error"] = f"Status {resp.status_code}"

    except Exception as e:
        elapsed = (time.time() - start) * 1000
        result["time_ms"] = elapsed
        result["error"] = str(e)

    return result

def run_load_test(args):
    print(f"\n{'='*60}")
    print(f"  Load Test Configuration")
    print(f"  URL       : {args.url}")
    print(f"  Users     : {args.users}")
    print(f"  Requests  : {args.requests}")
    print(f"  Method    : {args.method}")
    print(f"{'='*60}\n")

    headers = {"Content-Type": "application/json"}
    payload = json.loads(args.payload) if args.payload else None
    results = LoadTestResult()
    overall_start = time.time()
    
    # Thread management with Ramp-up
    futures = []
    with ThreadPoolExecutor(max_workers=args.users) as executor:
        for i in range(args.requests):
            # Optional: Ramp-up delay
            if args.ramp_up and i > 0:
                # Simple linear ramp-up logic
                pass 

            future = executor.submit(send_request, args.url, args.method, headers, payload, args.timeout, args.expect_json)
            futures.append(future)
            
            # Progress bar
            if args.verbose and (i + 1) % 100 == 0:
                print(f"  Submitted {i+1}/{args.requests} requests...")

        for i, future in enumerate(as_completed(futures), 1):
            res = future.result()
            results.times_ms.append(res["time_ms"])
            
            if res["success"]:
                results.successes += 1
            else:
                results.failures += 1
                if res["error"]:
                    results.errors.add(res["error"])
            
            if res["status"]:
                results.status_codes[res["status"]] = results.status_codes.get(res["status"], 0) + 1

    total_time = time.time() - overall_start
    times = results.times_ms

    # Calculation
    summary = {
        "Total Requests": args.requests,
        "Total Time (s)": round(total_time, 2),
        "Requests/sec": round(args.requests / total_time, 2),
        "Success Rate": f"{results.successes / args.requests * 100:.2f}%",
        "Failure Count": results.failures,
        "Latency Avg (ms)": round(statistics.mean(times), 2),
        "Latency Min (ms)": round(min(times), 2),
        "Latency Max (ms)": round(max(times), 2),
        "Latency P95 (ms)": round(sorted(times)[int(len(times) * 0.95)], 2),
        "Latency P99 (ms)": round(sorted(times)[int(len(times) * 0.99)], 2),
        "Std Dev (ms)": round(statistics.stdev(times), 2) if len(times) > 1 else 0,
        "Status Codes": results.status_codes,
        "Errors": list(results.errors)
    }

    # Print Report
    print(f"{'─'*60}")
    print(f"  Results Report")
    print(f"{'─'*60}")
    for k, v in summary.items():
        if k == "Status Codes":
            print(f"  {k}:")
            for code, count in v.items():
                print(f"    {code}: {count}")
        elif k == "Errors" and v:
            print(f"  {k}:")
            for err in v:
                print(f"    - {err[:80]}") # Truncate long errors
        else:
            print(f"  {k:<20}: {v}")
    print(f"{'─'*60}\n")

    return summary

def main():
    parser = argparse.ArgumentParser(description="Advanced Load Tester")
    parser.add_argument("--url", required=True, help="Target URL")
    parser.add_argument("--requests", type=int, default=100, help="Total requests")
    parser.add_argument("--users", type=int, default=10, help="Concurrent users")
    parser.add_argument("--method", default="GET", help="HTTP Method")
    parser.add_argument("--payload", help="JSON payload string")
    parser.add_argument("--timeout", type=int, default=10, help="Timeout in seconds")
    parser.add_argument("--expect-json", action="store_true", help="Validate response is valid JSON")
    parser.add_argument("--ramp-up", type=int, default=0, help="Ramp-up time in seconds (NYI)")
    parser.add_argument("--verbose", action="store_true", help="Show progress")
    
    args = parser.parse_args()
    run_load_test(args)

if __name__ == "__main__":
    main()
