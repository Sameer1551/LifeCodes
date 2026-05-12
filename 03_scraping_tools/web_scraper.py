#!/usr/bin/env python3
"""
web_scraper.py

A robust, reusable web‑scraping toolbox for developers.

Features:
* Auto-retry on failure (network resilience)
* Proxy support
* Basic page scraper (text or attributes)
* Pagination scraper
* Login‑and‑scrape helper
* JSON API collector
* Image / PDF downloader (with filename cleaning)
* Sitemap URL extractor

Dependencies:
    pip install requests beautifulsoup4 tqdm
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from tqdm import tqdm

# ----------------------------------------------------------------------
# Logging setup
# ----------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Helper utilities
# ----------------------------------------------------------------------
def _as_path(p: Union[str, Path]) -> Path:
    return Path(p).expanduser().resolve()


def _create_session(
    user_agent: str = None,
    proxy: str = None,
    retries: int = 3,
    backoff_factor: float = 0.5,
) -> requests.Session:
    """
    Create a robust requests.Session with:
    - Custom User-Agent
    - Proxy support
    - Automatic retry logic for 429/500 errors and connection failures
    """
    sess = requests.Session()
    
    # Retry strategy: retry on 429 (Too Many Requests), 500, 502, 503, 504
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    sess.mount("http://", adapter)
    sess.mount("https://", adapter)

    # User Agent
    ua = user_agent or (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
    sess.headers.update({"User-Agent": ua})

    # Proxy
    if proxy:
        sess.proxies = {
            "http": proxy,
            "https": proxy,
        }
        log.info(f"Using proxy: {proxy}")

    return sess


def _fetch(
    url: str,
    session: requests.Session,
    method: str = "GET",
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    json_body: Optional[Any] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
) -> requests.Response:
    """Low-level wrapper with logging."""
    log.debug(f"{method} {url}")
    resp = session.request(
        method.upper(),
        url,
        params=params,
        data=data,
        json=json_body,
        headers=headers,
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp


def _parse_html(content: str) -> BeautifulSoup:
    return BeautifulSoup(content, "html.parser")


def _extract_items(
    soup: BeautifulSoup, selector: str, attr: Optional[str] = None
) -> List[str]:
    """
    Extract items from BeautifulSoup.
    If attr is None -> return text content.
    If attr is provided -> return that attribute value.
    """
    elements = soup.select(selector)
    results = []
    for el in elements:
        if attr:
            val = el.get(attr)
            if val:
                results.append(val.strip())
        else:
            text = el.get_text(separator=" ", strip=True)
            if text:
                results.append(text)
    return results


def _download_file(
    url: str,
    dest_path: Path,
    session: requests.Session,
    chunk_size: int = 8192,
) -> Path:
    """Download url to dest_path with progress bar (if available)."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Clean filename: strip query params
    filename = Path(urllib.parse.urlparse(url).path).name
    if not filename:
        filename = "downloaded_file"
    dest_path = dest_path.parent / filename

    with session.get(url, stream=True, timeout=30) as r:
        r.raise_for_status()
        with dest_path.open("wb") as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
    return dest_path


# ----------------------------------------------------------------------
# 1️⃣  BASIC PAGE SCRAPER
# ----------------------------------------------------------------------
def basic_scrape(
    url: str,
    selectors: List[str],
    attr: Optional[str] = None,
    method: str = "GET",
    session: Optional[requests.Session] = None,
    proxy: str = None,
) -> Dict[str, List[str]]:
    """
    Fetch url, parse HTML, return mapping selector -> list of strings.
    """
    sess = session or _create_session(proxy=proxy)
    resp = _fetch(url, sess, method=method)
    soup = _parse_html(resp.text)

    results = {}
    for sel in selectors:
        results[sel] = _extract_items(soup, sel, attr=attr)
        log.info(f"Selector '{sel}' -> {len(results[sel])} items")
    return results


# ----------------------------------------------------------------------
# 2️⃣  PAGINATION SCRAPER
# ----------------------------------------------------------------------
def paginate_scrape(
    base_url: str,
    page_param: str,
    selectors: List[str],
    attr: Optional[str] = None,
    start_page: int = 1,
    max_pages: int = 10,
    delay: float = 1.0,
    session: Optional[requests.Session] = None,
    proxy: str = None,
) -> Dict[str, List[str]]:
    """
    Iterate through paginated pages.
    """
    sess = session or _create_session(proxy=proxy)
    aggregated: Dict[str, List[str]] = {sel: [] for sel in selectors}

    page = start_page
    while True:
        params = {page_param: page}
        log.info(f"Scraping page {page}...")
        try:
            resp = _fetch(base_url, sess, params=params)
            soup = _parse_html(resp.text)

            count = 0
            for sel in selectors:
                items = _extract_items(soup, sel, attr=attr)
                aggregated[sel].extend(items)
                count += len(items)

            # Stop if page seems empty
            if count == 0:
                log.warning("No items found on this page. Stopping.")
                break

            if max_pages and page >= start_page + max_pages - 1:
                log.info("Reached max_pages limit.")
                break

            page += 1
            time.sleep(delay)
        except Exception as e:
            log.error(f"Error on page {page}: {e}")
            break

    return aggregated


# ----------------------------------------------------------------------
# 3️⃣  LOGIN‑AND‑SCRAPE
# ----------------------------------------------------------------------
def login_and_scrape(
    login_url: str,
    payload: Dict[str, Any],
    target_url: str,
    selectors: List[str],
    attr: Optional[str] = None,
    session: Optional[requests.Session] = None,
    proxy: str = None,
) -> Dict[str, List[str]]:
    """
    Perform POST login then scrape target_url.
    """
    sess = session or _create_session(proxy=proxy)
    log.info("Logging in...")
    _fetch(login_url, sess, method="POST", data=payload)
    
    # Check login success? Usually we just try to fetch the target.
    log.info("Fetching protected target...")
    resp = _fetch(target_url, sess)
    soup = _parse_html(resp.text)

    out = {}
    for sel in selectors:
        out[sel] = _extract_items(soup, sel, attr=attr)
    return out


# ----------------------------------------------------------------------
# 4️⃣  API DATA COLLECTOR
# ----------------------------------------------------------------------
def api_fetch(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Any] = None,
    session: Optional[requests.Session] = None,
    proxy: str = None,
) -> Any:
    """
    Call a JSON API and return parsed response.
    """
    sess = session or _create_session(proxy=proxy)
    resp = _fetch(url, sess, method=method, headers=headers, params=params, json_body=json_body)
    return resp.json()


# ----------------------------------------------------------------------
# 5️⃣  IMAGE / PDF DOWNLOADER
# ----------------------------------------------------------------------
def download_assets(
    page_url: str,
    selector: str,
    attr: str,
    out_dir: Path,
    allowed_exts: Optional[List[str]] = None,
    proxy: str = None,
) -> List[Path]:
    """
    Generic asset downloader.
    """
    sess = _create_session(proxy=proxy)
    resp = _fetch(page_url, sess)
    soup = _parse_html(resp.text)

    urls = []
    for el in soup.select(selector):
        u = el.get(attr)
        if u:
            # Resolve relative URLs
            full_url = urllib.parse.urljoin(page_url, u)
            urls.append(full_url)

    log.info(f"Found {len(urls)} assets. Downloading...")
    out_dir = _as_path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    saved = []
    iterator = tqdm(urls, desc="Downloading")
    for u in iterator:
        # Clean filename: remove query params
        path_part = urllib.parse.urlparse(u).path
        filename = Path(path_part).name
        if not filename:
            filename = f"file_{len(saved)}"
        
        # Check extension
        if allowed_exts:
            ext = Path(filename).suffix.lower()
            if ext not in allowed_exts:
                continue

        dest = out_dir / filename
        try:
            _download_file(u, dest, sess)
            saved.append(dest)
        except Exception as e:
            log.error(f"Failed {u}: {e}")

    log.info(f"Downloaded {len(saved)} files to {out_dir}")
    return saved


# ----------------------------------------------------------------------
# 6️⃣  SITEMAP SCRAPER
# ----------------------------------------------------------------------
def scrape_sitemap(
    sitemap_url: str,
    proxy: str = None,
) -> List[str]:
    """
    Parse a sitemap.xml and return list of URLs.
    """
    sess = _create_session(proxy=proxy)
    resp = _fetch(sitemap_url, sess)
    soup = _parse_html(resp.text)
    
    # Standard sitemap tags
    urls = [loc.get_text() for loc in soup.find_all("url")]
    
    # Check for sitemap index (nested sitemaps)
    sitemap_locs = soup.find_all("sitemap")
    if sitemap_locs:
        log.info(f"Found {len(sitemap_locs)} nested sitemaps. Parsing recursively...")
        for loc in sitemap_locs:
            sub_url = loc.find_next("loc").get_text()
            urls.extend(scrape_sitemap(sub_url, proxy=proxy))
            
    return list(set(urls)) # Deduplicate


# ----------------------------------------------------------------------
# COMMAND‑LINE INTERFACE
# ----------------------------------------------------------------------
def _build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Robust web‑scraping toolbox.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--proxy", default=None, help="Proxy URL (e.g., http://localhost:8080)")
    
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    # ---- basic ----
    p_basic = subparsers.add_parser("basic", help="Extract data from a single page")
    p_basic.add_argument("url", help="Target page URL")
    p_basic.add_argument("--selector", action="append", required=True, help="CSS selector")
    p_basic.add_argument("--attr", default=None, help="Extract attribute value instead of text")
    p_basic.add_argument("--output", help="Save results to JSON file")
    p_basic.add_argument("--method", default="GET", choices=["GET", "POST"])

    # ---- paginate ----
    p_page = subparsers.add_parser("paginate", help="Scrape a paginated list")
    p_page.add_argument("base_url", help="Base URL (without page param)")
    p_page.add_argument("--page-param", required=True, help="Query param for page number")
    p_page.add_argument("--selector", action="append", required=True)
    p_page.add_argument("--attr", default=None, help="Extract attribute value")
    p_page.add_argument("--start", type=int, default=1)
    p_page.add_argument("--max-pages", type=int, default=10)
    p_page.add_argument("--delay", type=float, default=1.0)
    p_page.add_argument("--output", help="Save results to JSON file")

    # ---- login ----
    p_login = subparsers.add_parser("login", help="Login (POST) then scrape")
    p_login.add_argument("login_url", help="Login endpoint")
    p_login.add_argument("target_url", help="Protected page to scrape")
    p_login.add_argument("--payload", required=True, help="JSON login payload")
    p_login.add_argument("--selector", action="append", required=True)
    p_login.add_argument("--attr", default=None, help="Extract attribute value")
    p_login.add_argument("--output", help="Save results to JSON file")

    # ---- api ----
    p_api = subparsers.add_parser("api", help="Call a JSON API endpoint")
    p_api.add_argument("url", help="API endpoint")
    p_api.add_argument("--method", default="GET")
    p_api.add_argument("--headers", help="JSON headers string")
    p_api.add_argument("--params", help="JSON query params string")
    p_api.add_argument("--body", help="JSON body string (for POST/PUT)")
    p_api.add_argument("--output", help="Save results to JSON file")

    # ---- download-images ----
    p_img = subparsers.add_parser("download-images", help="Download images from page")
    p_img.add_argument("url", help="Page URL")
    p_img.add_argument("--selector", default="img", help="CSS selector for <img> tags")
    p_img.add_argument("--out-dir", required=True, help="Output directory")

    # ---- download-pdfs ----
    p_pdf = subparsers.add_parser("download-pdfs", help="Download PDFs from page")
    p_pdf.add_argument("url", help="Page URL")
    p_pdf.add_argument("--selector", default='a[href$=".pdf"]', help="CSS selector for PDF links")
    p_pdf.add_argument("--out-dir", required=True, help="Output directory")

    # ---- sitemap ----
    p_sitemap = subparsers.add_parser("sitemap", help="Extract URLs from sitemap.xml")
    p_sitemap.add_argument("url", help="Sitemap URL")
    p_sitemap.add_argument("--output", help="Save URLs to text file (one per line)")

    return parser


def _save_json(data: Any, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log.info(f"Saved results to {path}")


def _dispatch(args: argparse.Namespace) -> None:
    # Create reusable session if needed? 
    # We create sessions inside functions to ensure proxy arg is passed cleanly.
    try:
        if args.cmd == "basic":
            data = basic_scrape(
                url=args.url,
                selectors=args.selector,
                attr=args.attr,
                method=args.method,
                proxy=args.proxy,
            )
            if args.output:
                _save_json(data, Path(args.output))
            else:
                print(json.dumps(data, indent=2))

        elif args.cmd == "paginate":
            data = paginate_scrape(
                base_url=args.base_url,
                page_param=args.page_param,
                selectors=args.selector,
                attr=args.attr,
                start_page=args.start,
                max_pages=args.max_pages,
                delay=args.delay,
                proxy=args.proxy,
            )
            if args.output:
                _save_json(data, Path(args.output))
            else:
                print(json.dumps(data, indent=2))

        elif args.cmd == "login":
            payload = json.loads(args.payload)
            data = login_and_scrape(
                login_url=args.login_url,
                payload=payload,
                target_url=args.target_url,
                selectors=args.selector,
                attr=args.attr,
                proxy=args.proxy,
            )
            if args.output:
                _save_json(data, Path(args.output))
            else:
                print(json.dumps(data, indent=2))

        elif args.cmd == "api":
            headers = json.loads(args.headers) if args.headers else None
            params = json.loads(args.params) if args.params else None
            body = json.loads(args.body) if args.body else None
            data = api_fetch(
                url=args.url,
                method=args.method,
                headers=headers,
                params=params,
                json_body=body,
                proxy=args.proxy,
            )
            if args.output:
                _save_json(data, Path(args.output))
            else:
                print(json.dumps(data, indent=2))

        elif args.cmd == "download-images":
            download_assets(
                page_url=args.url,
                selector=args.selector,
                attr="src", # Always src for images
                out_dir=Path(args.out_dir),
                allowed_exts=[".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"],
                proxy=args.proxy,
            )

        elif args.cmd == "download-pdfs":
            download_assets(
                page_url=args.url,
                selector=args.selector,
                attr="href", # Always href for links
                out_dir=Path(args.out_dir),
                allowed_exts=[".pdf"],
                proxy=args.proxy,
            )

        elif args.cmd == "sitemap":
            urls = scrape_sitemap(args.url, proxy=args.proxy)
            log.info(f"Found {len(urls)} URLs.")
            if args.output:
                Path(args.output).write_text("\n".join(urls))
                log.info(f"Saved URLs to {args.output}")
            else:
                print("\n".join(urls))

        else:
            raise RuntimeError(f"Unknown command: {args.cmd}")

    except Exception as exc:
        log.error(f"Fatal error: {exc}")
        sys.exit(1)


def main() -> None:
    parser = _build_cli()
    args = parser.parse_args()
    _dispatch(args)


if __name__ == "__main__":
    main()
