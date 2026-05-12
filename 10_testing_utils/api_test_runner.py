#!/usr/bin/env python3
"""
api_test_runner.py
------------------
Advanced API test runner with JUnit XML support and JSON report output.
Supports loading test cases from a config file.

Usage:
    python api_test_runner.py --config tests.json --base-url http://localhost:8000
    python api_test_runner.py --junit-xml report.xml
"""

import argparse
import json
import os
import sys
import time
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any

# --- Core Test Logic ---

def run_single_test(test_case: Dict[str, Any], base_url: str) -> Dict[str, Any]:
    """Executes a single API test case."""
    url = base_url.rstrip("/") + test_case.get("endpoint", "/")
    method = test_case.get("method", "GET").upper()
    payload = test_case.get("payload")
    headers = test_case.get("headers", {"Content-Type": "application/json"})
    expected_status = test_case.get("expected_status", 200)
    timeout = test_case.get("timeout", 10)
    name = test_case.get("name", url)

    start_time = time.time()
    result = {
        "name": name,
        "url": url,
        "method": method,
        "status": "FAIL",
        "status_code": None,
        "latency_ms": 0,
        "message": "",
        "test_case": test_case
    }

    try:
        response = requests.request(method, url, json=payload, headers=headers, timeout=timeout)
        result["latency_ms"] = round((time.time() - start_time) * 1000, 2)
        result["status_code"] = response.status_code

        if response.status_code == expected_status:
            result["status"] = "PASS"
            result["message"] = f"OK ({expected_status})"
        else:
            result["status"] = "FAIL"
            result["message"] = f"Expected {expected_status}, got {response.status_code}. Body: {response.text[:100]}"

    except requests.exceptions.RequestException as e:
        result["status"] = "ERROR"
        result["message"] = str(e)

    return result

def run_suite(test_cases: List[Dict], base_url: str) -> List[Dict]:
    """Runs all test cases and prints a CLI report."""
    print(f"\n{'='*60}")
    print(f"  API Test Runner")
    print(f"  Base URL: {base_url}")
    print(f"{'='*60}")

    results = []
    passed = 0
    failed = 0
    start_time = time.time()

    for case in test_cases:
        res = run_single_test(case, base_url)
        results.append(res)

        if res["status"] == "PASS":
            passed += 1
            icon = "✅"
        else:
            failed += 1
            icon = "❌"
        
        print(f"  {icon} [{res['method']}] {case.get('endpoint', '/')} → {res['status_code']} ({res['latency_ms']}ms)")
        if res["status"] != "PASS":
            print(f"      ⚠ {res['message']}")

    total_time = round(time.time() - start_time, 2)
    
    print(f"\n{'─'*60}")
    print(f"  Summary: {passed}/{len(results)} passed in {total_time}s")
    print(f"{'─'*60}\n")
    
    return results

def save_junit_xml(results: List[Dict], filename: str):
    """Generates a JUnit XML report for CI/CD integration."""
    testsuites = ET.Element("testsuites")
    testsuite = ET.SubElement(testsuites, "testsuite", name="APITestSuite", tests=str(len(results)))
    
    failures = sum(1 for r in results if r["status"] != "PASS")
    testsuite.set("failures", str(failures))
    
    for res in results:
        testcase = ET.SubElement(testsuite, "testcase", name=res["name"], classname="API")
        testcase.set("time", str(res["latency_ms"] / 1000.0))
        
        if res["status"] != "PASS":
            failure = ET.SubElement(testcase, "failure", message=res["message"])
            failure.text = f"Status Code: {res['status_code']}\nMessage: {res['message']}"
    
    tree = ET.ElementTree(testsuites)
    tree.write(filename, encoding="utf-8", xml_declaration=True)
    print(f"JUnit XML report saved to {filename}")

def load_config(path: str) -> List[Dict]:
    """Loads test cases from a JSON file."""
    with open(path, "r") as f:
        return json.load(f).get("tests", [])

# --- CLI ---

def main():
    parser = argparse.ArgumentParser(description="API Test Runner")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="API Base URL")
    parser.add_argument("--config", help="Path to JSON config file with test cases")
    parser.add_argument("--junit-xml", help="Path to output JUnit XML report")
    
    args = parser.parse_args()

    # Env var overrides
    base_url = os.environ.get("API_BASE_URL", args.base_url)

    # Load cases
    if args.config:
        test_cases = load_config(args.config)
    else:
        # Default demo cases
        test_cases = [
            {"name": "Health Check", "endpoint": "/", "method": "GET", "expected_status": 200},
            {"name": "Users Endpoint", "endpoint": "/users", "method": "GET", "expected_status": 200},
            {"name": "404 Check", "endpoint": "/nonexistent", "method": "GET", "expected_status": 404},
        ]

    results = run_suite(test_cases, base_url)
    
    if args.junit_xml:
        save_junit_xml(results, args.junit_xml)
    
    # Exit with error code if failures exist
    if sum(1 for r in results if r["status"] != "PASS") > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
