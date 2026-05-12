# Simple logging demo (plain text)
python logger_setup.py demo

# Same demo but with JSON output
python logger_setup.py demo | grep '"level":"INFO"'

# Timer demo (default name “demo_block”, 0.75 s sleep)
python logger_setup.py timer-demo

# Error‑tracking demo (shows a full traceback)
python logger_setup.py error-demo




# additionla imports that can be used 
from logger_setup import get_logger, debug_params, performance_timer, error_tracker

log = get_logger(__name__, level=logging.DEBUG)

@debug_params(log)
@performance_timer("expensive", log)
@error_tracker(log)
def my_job(x: int):
    # Your code here …
    pass

