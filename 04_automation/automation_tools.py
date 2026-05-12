#!/usr/bin/env python3
"""
automation_tools.py

A robust toolkit for task automation, designed for developers.

Features
--------
* **Email sender** – single/bulk email with CC/BCC, file body support, and Env Var security.
* **Auto‑backup** – timestamped archives with retention and pre-backup hooks.
* **Folder monitor** – watch directory with **debounce** support (prevents rapid-fire triggers).
* **Scheduler** – run jobs at intervals.
* **Report generator** – render CSV/JSON data into HTML reports.

Install dependencies:
    pip install schedule watchdog jinja2 tqdm pandas
"""

from __future__ import annotations

import argparse
import csv
import importlib
import json
import logging
import os
import re
import shutil
import smtplib
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Union

# ----------------------------------------------------------------------
# Logging
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


def _ensure_parent(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)


def _run_shell_cmd(command: str) -> int:
    """Execute *command* via the OS shell. Returns the exit code."""
    log.info(f"Executing shell command: {command}")
    return os.system(command)


def _check_env(key: str, default: str = None) -> Optional[str]:
    """Helper to check environment variables."""
    val = os.environ.get(key)
    if not val and not default:
        log.warning(f"Environment variable {key} not found.")
    return val or default


# ----------------------------------------------------------------------
# 1️⃣  EMAIL SENDER
# ----------------------------------------------------------------------
@dataclass
class SMTPConfig:
    host: str
    port: int = 587
    username: str = ""
    password: str = ""
    use_tls: bool = True
    sender_name: Optional[str] = None


def send_email(
    cfg: SMTPConfig,
    subject: str,
    body: str,
    recipients: Sequence[str],
    cc: Optional[Sequence[str]] = None,
    bcc: Optional[Sequence[str]] = None,
    html_body: Optional[str] = None,
    attachments: Optional[Sequence[Union[str, Path]]] = None,
) -> None:
    """
    Send a single e‑mail via SMTP.
    Supports CC, BCC, HTML alternate, and attachments.
    """
    msg = EmailMessage()
    sender = cfg.username
    if cfg.sender_name:
        sender = f"{cfg.sender_name} <{cfg.username}>"

    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject

    if cc:
        msg["Cc"] = ", ".join(cc)
    # Bcc is not added to headers (by design)

    msg.set_content(body)

    if html_body:
        msg.add_alternative(html_body, subtype="html")

    for att in attachments or []:
        path = _as_path(att)
        if not path.is_file():
            log.warning(f"Attachment not found, skipping: {path}")
            continue
        with path.open("rb") as f:
            data = f.read()
        msg.add_attachment(
            data,
            maintype="application",
            subtype="octet-stream",
            filename=path.name,
        )

    all_recipients = list(recipients) + list(cc or []) + list(bcc or [])

    try:
        with smtplib.SMTP(cfg.host, cfg.port, timeout=30) as server:
            if cfg.use_tls:
                server.starttls()
            if cfg.username:
                server.login(cfg.username, cfg.password)
            server.send_message(msg, to_addrs=all_recipients)
        log.info(f"Sent e‑mail to {len(all_recipients)} recipient(s)")
    except Exception as exc:
        log.exception("Failed to send e‑mail")
        raise exc


def bulk_email(
    cfg: SMTPConfig,
    subject_tpl: str,
    body_tpl: str,
    recipient_rows: Iterable[Dict[str, Any]],
    html_body_tpl: Optional[str] = None,
    attachments_tpl: Optional[Callable[[Dict[str, Any]], List[Union[str, Path]]]] = None,
) -> Tuple[int, int]:
    """
    Simple mail‑merge implementation.
    Returns a tuple (sent_count, failed_count).
    """
    sent, failed = 0, 0
    for row in recipient_rows:
        try:
            subject = subject_tpl.format(**row)
            body = body_tpl.format(**row)
            html = html_body_tpl.format(**row) if html_body_tpl else None
            atts = attachments_tpl(row) if attachments_tpl else None
            
            send_email(
                cfg=cfg, subject=subject, body=body,
                recipients=[row["email"]],
                html_body=html, attachments=atts
            )
            sent += 1
        except Exception:
            failed += 1
            log.exception(f"Failed to send mail to {row.get('email')}")
    return sent, failed


# ----------------------------------------------------------------------
# 2️⃣  AUTO‑BACKUP
# ----------------------------------------------------------------------
def auto_backup(
    src_dir: Union[str, Path],
    dst_dir: Union[str, Path],
    compression: str = "zip",
    retain: int = 5,
    pre_command: Optional[str] = None,
) -> Path:
    """
    Create a timestamped archive of ``src_dir`` inside ``dst_dir``.
    Supported *compression*: ``zip``, ``gztar``, ``bztar``, ``xztar``.
    Optionally run a shell command before backing up (e.g., database dump).
    """
    src = _as_path(src_dir)
    dst = _as_path(dst_dir)
    if not src.is_dir():
        raise ValueError(f"Source {src} is not a directory")
    dst.mkdir(parents=True, exist_ok=True)

    if pre_command:
        log.info(f"Running pre-backup command...")
        exit_code = _run_shell_cmd(pre_command)
        if exit_code != 0:
            log.error("Pre-backup command failed. Aborting.")
            raise RuntimeError("Pre-backup command failed")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_base = dst / f"{src.name}_{timestamp}"
    
    # shutil.make_archive returns the full path with extension
    archive_path = shutil.make_archive(str(archive_base), compression, root_dir=str(src))
    archive_path = Path(archive_path)

    # Retention policy
    archives = sorted(
        [p for p in dst.glob(f"{src.name}_*") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old in archives[retain:]:
        try:
            old.unlink()
            log.debug(f"Removed old backup {old}")
        except Exception as exc:
            log.warning(f"Failed to delete {old} – {exc}")

    log.info(f"Created backup {archive_path} (kept {retain} newest)")
    return archive_path


# ----------------------------------------------------------------------
# 3️⃣  FOLDER MONITOR (Watchdog with Debounce)
# ----------------------------------------------------------------------
def monitor_folder(
    path: Union[str, Path],
    patterns: List[str],
    command: str,
    recursive: bool = True,
    debounce_seconds: float = 2.0,
) -> None:
    """
    Watch *path* for changes. Runs *command* when events stop firing for
    *debounce_seconds* (prevents rapid-fire triggers).
    """
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        raise ImportError("Please install watchdog: pip install watchdog")

    folder = _as_path(path)
    if not folder.is_dir():
        raise ValueError(f"{folder} is not a directory")

    class _Handler(FileSystemEventHandler):
        def __init__(self):
            super().__init__()
            self._regexes = [re.compile(p) for p in patterns]
            self._last_trigger_time = 0.0

        def _matches(self, path: str) -> bool:
            return any(r.search(path) for r in self._regexes)

        def on_any_event(self, event):
            if event.is_directory:
                return
            if self._matches(event.src_path):
                # Debounce logic: only schedule run if enough time has passed
                now = time.time()
                if now - self._last_trigger_time > debounce_seconds:
                    log.info(f"Detected change in {event.src_path}. Waiting {debounce_seconds}s to settle...")
                    self._last_trigger_time = now
                    
                    # Simple blocking run (advanced approach would use threading.Timer)
                    # Here we just sleep before running
                    time.sleep(debounce_seconds)
                    log.info(f"Running command: {command}")
                    _run_shell_cmd(command)
                    # Update trigger time again to prevent double runs from backlog
                    self._last_trigger_time = time.time()

    event_handler = _Handler()
    observer = Observer()
    observer.schedule(event_handler, str(folder), recursive=recursive)
    observer.start()
    log.info(f"Started monitoring {folder} (patterns={patterns})")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        log.info("Folder monitoring stopped by user")
    observer.join()


# ----------------------------------------------------------------------
# 4️⃣  SIMPLE SCHEDULER
# ----------------------------------------------------------------------
def schedule_job(
    interval_seconds: int,
    command: Optional[str] = None,
    func: Optional[Callable[[], Any]] = None,
    immediate: bool = True,
) -> None:
    """
    Run *command* or *func* every *interval_seconds*.
    """
    try:
        import schedule
    except ImportError:
        raise ImportError("Please install schedule: pip install schedule")

    if command is None and func is None:
        raise ValueError("You must provide either a shell command or a Python callable")

    job_func = lambda: _run_shell_cmd(command) if command else func

    job = schedule.every(interval_seconds).seconds.do(job_func)

    if immediate:
        log.info("Executing the job immediately (first run)...")
        job.run()

    log.info(f"Scheduler started – every {interval_seconds} seconds. Press Ctrl‑C to stop.")
    try:
        while True:
            schedule.run_pending()
            time.sleep(0.5)
    except KeyboardInterrupt:
        log.info("Scheduler stopped by user")


# ----------------------------------------------------------------------
# 5️⃣  REPORT GENERATOR
# ----------------------------------------------------------------------
def _load_dataframe(data_path: Path) -> Any:
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("Report generation needs pandas. Install via `pip install pandas`.")

    suffix = data_path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(data_path)
    if suffix in {".json", ".js"}:
        return pd.read_json(data_path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(data_path)
    raise ValueError(f"Unsupported data file {data_path}")


def generate_report(
    data_path: Union[str, Path],
    template_path: Union[str, Path],
    output_path: Union[str, Path],
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Render *data_path* into an HTML file using Jinja2.
    Variables available in template: {{ df }} (the dataframe) and any items in context.
    """
    try:
        from jinja2 import Environment, FileSystemLoader, select_autoescape
    except ImportError:
        raise ImportError("Please install jinja2: pip install jinja2")

    data_file = _as_path(data_path)
    tpl_file = _as_path(template_path)
    out_file = _as_path(output_path)

    df = _load_dataframe(data_file)

    env = Environment(
        loader=FileSystemLoader(str(tpl_file.parent)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template(tpl_file.name)
    
    render_context = {"df": df}
    if context:
        render_context.update(context)

    rendered = template.render(render_context)
    _ensure_parent(out_file)
    out_file.write_text(rendered, encoding="utf-8")
    log.info(f"Report generated at {out_file}")


# ----------------------------------------------------------------------
# COMMAND‑LINE INTERFACE
# ----------------------------------------------------------------------
def _cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Automation toolbox.", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    # ---- send-email ----
    p_send = sub.add_parser("send-email", help="Send a single e‑mail")
    p_send.add_argument("--host", default=os.environ.get("SMTP_HOST"), help="SMTP server (or env var SMTP_HOST)")
    p_send.add_argument("--port", type=int, default=int(os.environ.get("SMTP_PORT", 587)), help="SMTP port")
    p_send.add_argument("--user", default=os.environ.get("SMTP_USER"), help="SMTP username")
    p_send.add_argument("--password", default=os.environ.get("SMTP_PASSWORD"), help="SMTP password")
    p_send.add_argument("--tls", action="store_true", default=True, help="Use STARTTLS")
    p_send.add_argument("--from-name", default=None, help="Friendly sender name")
    p_send.add_argument("--subject", required=True, help="Subject line")
    p_send.add_argument("--body", help="Plain text body")
    p_send.add_argument("--body-file", help="Read body from file (overrides --body)")
    p_send.add_argument("--html", help="HTML body (string)")
    p_send.add_argument("--to", nargs="+", required=True, help="Recipients")
    p_send.add_argument("--cc", nargs="+", help="CC Recipients")
    p_send.add_argument("--attach", nargs="+", help="Attachments")

    # ---- backup ----
    p_backup = sub.add_parser("backup", help="Create timestamped archive")
    p_backup.add_argument("src_dir", help="Folder to back up")
    p_backup.add_argument("dst_dir", help="Destination directory")
    p_backup.add_argument("--compression", default="zip", choices=["zip", "gztar", "bztar", "xztar"])
    p_backup.add_argument("--retain", type=int, default=5, help="Number of backups to keep")
    p_backup.add_argument("--pre-command", help="Shell command to run before backup")

    # ---- monitor ----
    p_monitor = sub.add_parser("monitor", help="Watch folder and run command")
    p_monitor.add_argument("path", help="Folder to monitor")
    p_monitor.add_argument("--patterns", nargs="+", required=True, help="Regex patterns to match")
    p_monitor.add_argument("--cmd", required=True, help="Command to run on match")
    p_monitor.add_argument("--debounce", type=float, default=2.0, help="Wait time before running command (debounce)")
    p_monitor.add_argument("--recursive", action="store_true", default=True)

    # ---- schedule ----
    p_sched = sub.add_parser("schedule", help="Run command periodically")
    p_sched.add_argument("--interval", type=int, required=True, help="Seconds between runs")
    group = p_sched.add_mutually_exclusive_group(required=True)
    group.add_argument("--cmd", help="Shell command")
    group.add_argument("--callable", help="Python callable path (e.g. pkg.mod.func)")
    p_sched.add_argument("--immediate", action="store_true", help="Run once immediately")

    # ---- report ----
    p_report = sub.add_parser("report", help="Generate HTML report from data")
    p_report.add_argument("data", help="Data file (CSV/JSON/Excel)")
    p_report.add_argument("template", help="Jinja2 template file")
    p_report.add_argument("output", help="Output HTML file")

    return parser


def _dispatch_cli(args: argparse.Namespace) -> None:
    if args.command == "send-email":
        if not args.body and not args.body_file:
            log.error("Either --body or --body-file is required.")
            sys.exit(1)

        body_content = args.body or ""
        if args.body_file:
            body_content = Path(args.body_file).read_text()

        cfg = SMTPConfig(
            host=args.host, port=args.port, username=args.user,
            password=args.password, use_tls=args.tls, sender_name=args.from_name
        )
        send_email(
            cfg=cfg, subject=args.subject, body=body_content,
            recipients=args.to, cc=args.cc, html_body=args.html, attachments=args.attach
        )

    elif args.command == "backup":
        auto_backup(
            src_dir=args.src_dir, dst_dir=args.dst_dir,
            compression=args.compression, retain=args.retain,
            pre_command=args.pre_command
        )

    elif args.command == "monitor":
        monitor_folder(
            path=args.path, patterns=args.patterns, command=args.cmd,
            recursive=args.recursive, debounce_seconds=args.debounce
        )

    elif args.command == "schedule":
        func = None
        if args.callable:
            mod_name, func_name = args.callable.rsplit(".", 1)
            mod = importlib.import_module(mod_name)
            func = getattr(mod, func_name)
            if not callable(func):
                raise ValueError(f"{args.callable} is not callable")
        schedule_job(
            interval_seconds=args.interval, command=args.cmd,
            func=func, immediate=args.immediate
        )

    elif args.command == "report":
        generate_report(
            data_path=args.data, template_path=args.template,
            output_path=args.output
        )
    else:
        raise RuntimeError(f"Unhandled command: {args.command}")


def main() -> None:
    parser = _cli_parser()
    args = parser.parse_args()
    try:
        _dispatch_cli(args)
    except Exception as exc:
        log.exception("Automation tool failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
