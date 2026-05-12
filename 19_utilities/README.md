# 19_utilities

## Purpose
Miscellaneous utility tools: data generation, UUIDs, password checking, QR codes, scheduling, clipboard, system info, JSON validation, and markdown conversion.

## Files
- `random_data_generator.py` – generate fake datasets (CSV, JSON, SQL)
- `uuid_generator.py` – generate UUID v1/v4/v7 and ULIDs
- `password_strength_checker.py` – evaluate password strength and entropy
- `qr_code_generator.py` – generate QR codes (PNG, SVG, ASCII)
- `qr_code_reader.py` – read QR codes from images (requires OpenCV or pyzbar)
- `time_scheduler.py` – schedule tasks (cron, interval, one-shot)
- `clipboard_manager.py` – clipboard history and operations
- `system_info_reporter.py` – system information report
- `json_validator.py` – validate and format JSON
- `markdown_to_html_converter.py` – convert Markdown to HTML

## How to run
1. Install Python 3.8+.
2. Open terminal in `19_utilities`.
3. Run any script, e.g. `python uuid_generator.py --count 10`.