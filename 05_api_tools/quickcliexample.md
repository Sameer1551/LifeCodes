# Simple logging demo (plain text)
python logger_setup.py demo

# Same demo but with JSON output
python logger_setup.py demo | grep '"level":"INFO"'

# Timer demo (default name “demo_block”, 0.75 s sleep)
python logger_setup.py timer-demo

# Error‑tracking demo (shows a full traceback)
python logger_setup.py error-demo









