#!/usr/bin/env python3
"""
Screenshot Capture Tool
Take automated screenshots of websites or desktop.
"""

import argparse
from pathlib import Path

# mss for desktop screenshots
try:
    import mss
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

# playwright for web screenshots
try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


def capture_desktop(
    output_path: str,
    monitor: int = 0,
    region: tuple[int, int, int, int] | None = None
) -> str:
    """
    Capture a screenshot of the desktop.

    Args:
        output_path: Path to save screenshot.
        monitor: Monitor number (0 = all monitors, 1 = primary).
        region: Tuple (left, top, width, height) for region capture.

    Returns:
        Path to screenshot file.
    """
    if not HAS_MSS:
        raise ImportError("mss library is required. Install with: pip install mss")

    with mss.mss() as sct:
        if region:
            # Capture specific region
            screenshot = sct.grab({
                'left': region[0],
                'top': region[1],
                'width': region[2],
                'height': region[3]
            })
        else:
            # Capture monitor
            monitors = sct.monitors
            if monitor >= len(monitors):
                monitor = 1  # Fall back to primary monitor

            if monitor == 0:
                # Capture all monitors combined
                screenshot = sct.grab(monitors[0])
            else:
                screenshot = sct.grab(monitors[monitor])

        # Save screenshot
        from PIL import Image
        img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
        img.save(output_path)

    return output_path


def capture_website(
    url: str,
    output_path: str,
    full_page: bool = False,
    delay: float = 2.0,
    viewport_width: int = 1920,
    viewport_height: int = 1080,
    selector: str | None = None
) -> str:
    """
    Capture a screenshot of a website.

    Args:
        url: URL to capture.
        output_path: Path to save screenshot.
        full_page: Capture full page (not just viewport).
        delay: Time to wait for page load (seconds).
        viewport_width: Browser viewport width.
        viewport_height: Browser viewport height.
        selector: CSS selector to capture specific element.

    Returns:
        Path to screenshot file.
    """
    if not HAS_PLAYWRIGHT:
        raise ImportError(
            "playwright library is required. Install with: pip install playwright && playwright install"
        )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': viewport_width, 'height': viewport_height})

        try:
            page.goto(url, wait_until='networkidle', timeout=30000)
            page.wait_for_timeout(int(delay * 1000))

            if selector:
                # Capture specific element
                element = page.locator(selector)
                element.screenshot(path=output_path)
            elif full_page:
                # Full page screenshot
                page.screenshot(path=output_path, full_page=True)
            else:
                # Viewport screenshot
                page.screenshot(path=output_path)
        finally:
            browser.close()

    return output_path


def capture_desktop_multiple(
    output_dir: str,
    monitors: list[int] | None = None,
    prefix: str = "screenshot"
) -> list[str]:
    """
    Capture screenshots of multiple monitors.

    Args:
        output_dir: Directory to save screenshots.
        monitors: List of monitor numbers, or None for all.
        prefix: Filename prefix.

    Returns:
        List of paths to screenshot files.
    """
    if not HAS_MSS:
        raise ImportError("mss library is required. Install with: pip install mss")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    saved_paths = []

    with mss.mss() as sct:
        available_monitors = list(range(1, len(sct.monitors)))

        if monitors is None:
            monitors = available_monitors

        for mon in monitors:
            if mon in available_monitors:
                out_file = output_path / f"{prefix}_monitor_{mon}.png"
                screenshot = sct.grab(sct.monitors[mon])

                from PIL import Image
                img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
                img.save(str(out_file))

                saved_paths.append(str(out_file))

    return saved_paths


def main():
    parser = argparse.ArgumentParser(
        description="Capture screenshots of desktop or websites."
    )

    # Mode selection
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--desktop",
        action="store_true",
        help="Capture desktop screenshot"
    )
    mode_group.add_argument(
        "--url",
        type=str,
        help="URL to capture website screenshot"
    )

    # Desktop options
    parser.add_argument(
        "--monitor",
        type=int,
        default=1,
        help="Monitor number (0=all monitors, 1=primary, default: 1)"
    )
    parser.add_argument(
        "--region",
        type=str,
        help="Region to capture as 'left,top,width,height'"
    )

    # Web options
    parser.add_argument(
        "--full-page",
        action="store_true",
        help="Capture full page (websites only)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay for page load in seconds (default: 2.0)"
    )
    parser.add_argument(
        "--viewport-width",
        type=int,
        default=1920,
        help="Browser viewport width (default: 1920)"
    )
    parser.add_argument(
        "--viewport-height",
        type=int,
        default=1080,
        help="Browser viewport height (default: 1080)"
    )
    parser.add_argument(
        "--selector",
        type=str,
        help="CSS selector to capture specific element"
    )

    # Output
    parser.add_argument(
        "-o", "--output",
        type=str,
        required=True,
        help="Output file path"
    )

    args = parser.parse_args()

    # Parse region if provided
    region = None
    if args.region:
        try:
            parts = [int(x.strip()) for x in args.region.split(',')]
            if len(parts) == 4:
                region = tuple(parts)
            else:
                parser.error("Region must be 'left,top,width,height'")
        except ValueError:
            parser.error("Region must be 'left,top,width,height' with integer values")

    try:
        if args.desktop:
            if not HAS_MSS:
                print("Error: mss library is required for desktop screenshots.")
                print("Install with: pip install mss")
                return

            capture_desktop(
                args.output,
                monitor=args.monitor,
                region=region
            )
            print(f"Desktop screenshot saved to {args.output}")

        elif args.url:
            if not HAS_PLAYWRIGHT:
                print("Error: playwright library is required for web screenshots.")
                print("Install with: pip install playwright && playwright install")
                return

            capture_website(
                args.url,
                args.output,
                full_page=args.full_page,
                delay=args.delay,
                viewport_width=args.viewport_width,
                viewport_height=args.viewport_height,
                selector=args.selector
            )
            print(f"Website screenshot saved to {args.output}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()