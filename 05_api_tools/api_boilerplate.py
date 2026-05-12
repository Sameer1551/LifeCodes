#!/usr/bin/env python3
"""
api_boilerplate.py

A robust, production-ready toolkit for building API clients and testing them.

Features:
* `APIClient` – Stateful client with connection pooling, retries, and auth.
* `TokenManager` – OAuth2 client-credentials flow with auto-refresh.
* `RateLimiter` – Efficient O(1) token-bucket implementation.
* `MockServer` – Simple local server for offline API testing.

Dependencies:
    pip install requests tenacity python-dateutil
"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import threading
import time
from dataclasses import dataclass, field
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional, Tuple, Union
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ----------------------------------------------------------------------
# Optional imports
# ----------------------------------------------------------------------
try:
    from tenacity import retry as _tenacity_retry, stop_after_attempt, wait_exponential
except ImportError:
    _tenacity_retry = None

try:
    from dateutil import parser as dt_parser
except ImportError:
    dt_parser = None

# ----------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s – %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 1️⃣  API CLIENT (Production Ready)
# ----------------------------------------------------------------------
@dataclass
class APIClient:
    """
    A robust API client using requests.Session for connection pooling.
    """
    base_url: str
    default_headers: Mapping[str, str] = field(default_factory=dict)
    token: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    
    # Internal session
    _session: Optional[requests.Session] = field(default=None, init=False, repr=False)

    def __post_init__(self):
        self._session = requests.Session()
        # Configure retry strategy for transport errors (connection refused, etc.)
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

    def _prepare_headers(self, headers: Optional[Mapping[str, str]]) -> Dict[str, str]:
        hdrs = dict(self.default_headers)
        if self.token:
            hdrs["Authorization"] = f"Bearer {self.token}"
        if headers:
            hdrs.update(headers)
        return hdrs

    def request(
        self,
        method: str,
        endpoint: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        json_body: Optional[Any] = None,
        data: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        raw_response: bool = False,
        **kwargs,
    ) -> Union[requests.Response, Dict, str]:
        """
        Send request. Returns JSON dict by default, or raw Response if raw_response=True.
        """
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        hdrs = self._prepare_headers(headers)

        try:
            resp = self._session.request(
                method,
                url,
                params=params,
                json=json_body,
                data=data,
                headers=hdrs,
                timeout=self.timeout,
                **kwargs,
            )
            resp.raise_for_status()

            if raw_response:
                return resp
            
            # Try JSON parse, fallback to text
            try:
                return resp.json()
            except json.JSONDecodeError:
                return resp.text

        except requests.RequestException as exc:
            log.error(f"Request failed: {exc}")
            raise

    # Convenience methods
    def get(self, endpoint: str, **kwargs) -> Any: return self.request("GET", endpoint, **kwargs)
    def post(self, endpoint: str, **kwargs) -> Any: return self.request("POST", endpoint, **kwargs)
    def put(self, endpoint: str, **kwargs) -> Any: return self.request("PUT", endpoint, **kwargs)
    def delete(self, endpoint: str, **kwargs) -> Any: return self.request("DELETE", endpoint, **kwargs)


# ----------------------------------------------------------------------
# 2️⃣  TOKEN MANAGER (OAuth2)
# ----------------------------------------------------------------------
@dataclass
class TokenManager:
    """
    Handles OAuth2 client-credentials flow with auto-refresh.
    Thread-safe implementation.
    """
    token_url: str
    client_id: str
    client_secret: str
    scope: Optional[str] = None
    
    _token: Optional[str] = field(default=None, init=False, repr=False)
    _expires_at: float = field(default=0.0, init=False)  # timestamp
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def get_token(self) -> str:
        with self._lock:
            now = time.time()
            # Refresh 30 seconds before expiry
            if self._token and self._expires_at > (now + 30):
                return self._token

            log.info("Requesting new OAuth2 token...")
            resp = requests.post(
                self.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": self.scope,
                },
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
            
            self._token = data["access_token"]
            # Calculate expiry
            expires_in = data.get("expires_in", 3600)
            self._expires_at = now + expires_in
            return self._token


# ----------------------------------------------------------------------
# 3️⃣  RATE LIMITER (Token Bucket O(1))
# ----------------------------------------------------------------------
class RateLimiter:
    """
    Thread-safe Token Bucket rate limiter.
    Does NOT grow memory over time unlike list-based implementations.
    """
    def __init__(self, rate: float, capacity: int):
        """
        :param rate: Tokens added per second.
        :param capacity: Maximum burst size.
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_time = time.time()
        self.lock = threading.Lock()

    def __call__(self, func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            self.acquire()
            return func(*args, **kwargs)
        return wrapper

    def acquire(self) -> None:
        """Block until a token is available."""
        with self.lock:
            now = time.time()
            # Refill tokens based on time elapsed
            elapsed = now - self.last_time
            self.tokens += elapsed * self.rate
            self.tokens = min(self.tokens, self.capacity)
            self.last_time = now

            if self.tokens < 1:
                # Calculate wait time
                wait_time = (1 - self.tokens) / self.rate
                time.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= 1


# ----------------------------------------------------------------------
# 4️⃣  MOCK SERVER (For Offline Testing)
# ----------------------------------------------------------------------
class MockAPIHandler(SimpleHTTPRequestHandler):
    """
    Serves JSON files from a directory. 
    Maps /api/users -> ./mocks/api/users.json
    """
    def do_GET(self):
        # Translate path to file
        # Remove leading slash
        path = self.path.lstrip('/')
        # Mock file path
        mock_file = Path("mocks") / f"{path}.json"
        
        if mock_file.exists():
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(mock_file.read_bytes())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"error": "Mock not found"}')

    def log_message(self, format, *args):
        # Override to use our logger
        log.info(f"MockServer: {args[0]}")


def run_mock_server(port: int = 8000):
    """Starts a simple server for offline testing."""
    server = HTTPServer(('localhost', port), MockAPIHandler)
    log.info(f"Mock API Server running on http://localhost:{port}")
    log.info("Place JSON files in './mocks/' (e.g. ./mocks/api/users.json)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()


# ----------------------------------------------------------------------
# 5️⃣  RETRY DECORATOR
# ----------------------------------------------------------------------
def retry(
    attempts: int = 3,
    backoff: float = 1.0,
    exceptions: Tuple = (requests.RequestException,)
) -> Callable:
    """Decorator with exponential backoff."""
    if _tenacity_retry:
        return _tenacity_retry(
            reraise=True,
            stop=stop_after_attempt(attempts),
            wait=wait_exponential(multiplier=backoff)
        )
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exc = None
            for i in range(attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    wait = backoff * (2 ** i)
                    log.warning(f"Attempt {i+1}/{attempts} failed. Retrying in {wait}s...")
                    time.sleep(wait)
            raise last_exc
        return wrapper
    return decorator


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="API Toolkit", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    # Request
    p_req = sub.add_parser("request", help="Make an HTTP request")
    p_req.add_argument("method", choices=["GET", "POST", "PUT", "DELETE"])
    p_req.add_argument("url")
    p_req.add_argument("--json", help="JSON body")
    p_req.add_argument("--token", help="Bearer token")

    # Token
    p_tok = sub.add_parser("token", help="Get OAuth2 token")
    p_tok.add_argument("token_url")
    p_tok.add_argument("client_id")
    p_tok.add_argument("client_secret")

    # Mock Server
    p_mock = sub.add_parser("serve", help="Run a local Mock API Server")
    p_mock.add_argument("--port", type=int, default=8000)

    # Rate Demo
    p_rate = sub.add_parser("rate-demo", help="Demo Rate Limiter")
    p_rate.add_argument("--rate", type=float, default=2.0, help="Requests per second")
    p_rate.add_argument("--count", type=int, default=5, help="Number of calls")

    return parser

def _dispatch(args):
    if args.command == "request":
        client = APIClient(base_url="", token=args.token)
        # Extract path from URL
        parsed = urlparse(args.url)
        # We treat everything as path relative to base for the wrapper
        # But here we effectively do a raw request
        
        # Hack: APIClient is for base_url, let's do manual request for CLI
        hdrs = {}
        if args.token: hdrs["Authorization"] = f"Bearer {args.token}"
        resp = requests.request(args.method, args.url, json=json.loads(args.json) if args.json else None, headers=hdrs)
        print(resp.text)

    elif args.command == "token":
        tm = TokenManager(args.token_url, args.client_id, args.client_secret)
        print(tm.get_token())

    elif args.command == "serve":
        run_mock_server(args.port)

    elif args.command == "rate-demo":
        limiter = RateLimiter(rate=args.rate, capacity=1)
        
        @limiter
        def task(i):
            print(f"Call {i} executed at {time.time():.2f}")
        
        start = time.time()
        for i in range(args.count):
            task(i)
        print(f"Finished {args.count} calls in {time.time() - start:.2f}s")

def main():
    parser = _build_parser()
    args = parser.parse_args()
    try:
        _dispatch(args)
    except Exception as e:
        log.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
