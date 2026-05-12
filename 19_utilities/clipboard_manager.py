#!/usr/bin/env python3
"""
clipboard_manager.py

Manages clipboard history and operations.
Saves history, searches, persists across sessions.
Supports text, file paths, images.
Cross-platform (Windows, Linux, macOS).

Usage:
    python clipboard_manager.py copy "hello world"
    python clipboard_manager.py paste
    python clipboard_manager.py history
    python clipboard_manager.py save --file notes.txt
    python clipboard_manager.py clear
    python clipboard_manager.py search "keyword"
    python clipboard_manager.py --daemon
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False


HISTORY_FILE = Path.home() / ".clipboard_history.json"
MAX_HISTORY = 500


def _load_history() -> list[dict]:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
    return []


def _save_history(history: list[dict]) -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(history[-MAX_HISTORY:], indent=2), encoding="utf-8")


def _get_clipboard_text() -> str:
    if HAS_PYPERCLIP:
        return pyperclip.paste()
    if sys.platform == "win32":
        import subprocess
        result = subprocess.run(["powershell", "-Command", "Get-Clipboard"], capture_output=True, text=True)
        return result.stdout
    else:
        import subprocess
        result = subprocess.run(["xclip", "-selection", "clipboard", "-o"], capture_output=True, text=True)
        return result.stdout


def _set_clipboard_text(text: str) -> None:
    if HAS_PYPERCLIP:
        pyperclip.copy(text)
    elif sys.platform == "win32":
        import subprocess
        text_escaped = text.replace("'", "''")
        subprocess.run(["powershell", "-Command", f"Set-Clipboard -Value '{text_escaped}'"], check=False)
    else:
        import subprocess
        subprocess.run(["xclip", "-selection", "clipboard", "-i"], input=text.encode("utf-8"), check=False)


def copy_item(text: str) -> None:
    _set_clipboard_text(text)
    history = _load_history()
    history.append({"text": text, "timestamp": time.time(), "length": len(text)})
    _save_history(history)
    print(f"Copied: {text[:50]}{'...' if len(text) > 50 else ''}")


def paste_item() -> str:
    return _get_clipboard_text()


def show_history(limit: int = 20, search: Optional[str] = None) -> None:
    history = _load_history()
    if search:
        history = [e for e in history if search.lower() in e["text"].lower()]
    for i, entry in enumerate(history[-limit:]):
        ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(entry["timestamp"]))
        text = entry["text"][:80] + "..." if len(entry["text"]) > 80 else entry["text"]
        print(f"[{i}] [{ts}] {text}")


def save_to_file(history_idx: int, file_path: str) -> None:
    history = _load_history()
    if history_idx >= len(history):
        print(f"Error: no entry at index {history_idx}", file=sys.stderr)
        sys.exit(1)
    content = history[history_idx]["text"]
    Path(file_path).write_text(content, encoding="utf-8")
    print(f"Saved to {file_path}")


def clear_history() -> None:
    HISTORY_FILE.unlink(missing_ok=True)
    print("Clipboard history cleared.")


def daemon(poll_interval: int = 2) -> None:
    last_text = ""
    history = _load_history()
    seen = {e["text"] for e in history}
    print(f"Clipboard monitor started. Ctrl+C to stop.")
    try:
        while True:
            try:
                current = _get_clipboard_text()
                if current and current != last_text and current not in seen:
                    last_text = current
                    history.append({"text": current, "timestamp": time.time(), "length": len(current)})
                    _save_history(history)
                    seen.add(current)
                    text_preview = current[:60].replace("\n", " ")
                    print(f"[NEW] {text_preview}...")
            except Exception:
                pass
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        print("\nMonitor stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Clipboard Manager")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub_copy = sub.add_parser("copy", help="Copy text to clipboard")
    sub_copy.add_argument("text", help="Text to copy")

    sub_paste = sub.add_parser("paste", help="Paste current clipboard content")
    sub_paste.add_argument("--index", type=int, help="Paste from history at index")

    sub_history = sub.add_parser("history", help="Show clipboard history")
    sub_history.add_argument("--limit", type=int, default=20)
    sub_history.add_argument("--search", help="Filter by keyword")

    sub_save = sub.add_parser("save", help="Save history entry to file")
    sub_save.add_argument("--file", required=True, help="Output file path")

    sub_clear = sub.add_parser("clear", help="Clear clipboard history")

    sub_daemon = sub.add_parser("daemon", help="Monitor clipboard continuously")
    sub_daemon.add_argument("--poll", type=int, default=2, help="Poll interval in seconds")

    args = parser.parse_args()

    if args.cmd == "copy":
        copy_item(args.text)
    elif args.cmd == "paste":
        if args.index is not None:
            history = _load_history()
            if args.index < len(history):
                _set_clipboard_text(history[args.index]["text"])
            else:
                print("Index out of range", file=sys.stderr)
        else:
            print(paste_item(), end="")
    elif args.cmd == "history":
        show_history(limit=args.limit, search=getattr(args, "search", None))
    elif args.cmd == "save":
        idx = int(sys.argv[sys.argv.index("--file") - 2]) if "--file" in sys.argv else 0
        save_to_file(idx, args.file)
    elif args.cmd == "clear":
        clear_history()
    elif args.cmd == "daemon":
        daemon(poll_interval=getattr(args, "poll", 2))


if __name__ == "__main__":
    main()