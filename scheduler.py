import os
import time
import subprocess
import logging
from datetime import datetime, timezone, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# IST = UTC+5:30
IST = timezone(timedelta(hours=5, minutes=30))

# ── Schedule config ───────────────────────────────────────────────────────────
RUN_HOUR   = 23           # 11:30 PM IST
RUN_MINUTE = 30
RUN_DAYS   = {0, 1, 2, 3, 4, 5, 6}  # Every day (Mon=0 ... Sun=6)

# Sentinel file: created after first run. Stored in persistent /app/storage.
_STORAGE_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage")
SENTINEL_FILE = os.path.join(_STORAGE_DIR, ".first_run_done")


def run_screener():
    logging.info("Starting scheduled screener runs...")
    try:
        logging.info("Running LONG strategy...")
        subprocess.run(["python", "screener.py", "--strategy", "long_breakout"], check=True)

        logging.info("Running SHORT strategy...")
        subprocess.run(["python", "screener.py", "--strategy", "short_breakout"], check=True)

        logging.info("Scheduled runs complete.")
    except Exception as e:
        logging.error(f"Error during screener runs: {e}")


def seconds_until_next_run() -> float:
    """Return seconds until the next 23:30 IST."""
    now    = datetime.now(IST)
    target = now.replace(hour=RUN_HOUR, minute=RUN_MINUTE, second=0, microsecond=0)

    # If we haven't passed 23:30 today, run today
    if now < target:
        return (target - now).total_seconds()

    # Otherwise run tomorrow at 23:30
    return (target + timedelta(days=1) - now).total_seconds()


if __name__ == "__main__":
    logging.info("Swing Trading System scheduler starting...")
    os.makedirs(_STORAGE_DIR, exist_ok=True)

    # ── First-deployment run ──────────────────────────────────────────────────
    # Run immediately on first startup (sentinel file absent = fresh deployment)
    if not os.path.exists(SENTINEL_FILE):
        logging.info("First deployment detected — running screener immediately.")
        run_screener()
        # Mark as done so future restarts don't re-trigger this
        with open(SENTINEL_FILE, "w") as f:
            f.write(datetime.now(IST).strftime("%d-%m-%Y %H:%M IST"))
        logging.info("Sentinel file written. Future runs will follow the 23:30 IST schedule.")
    else:
        logging.info("Returning deployment — skipping immediate run.")

    # ── Daily schedule loop ───────────────────────────────────────────────────
    while True:
        wait     = seconds_until_next_run()
        next_run = datetime.now(IST) + timedelta(seconds=wait)
        logging.info(f"Next run: {next_run.strftime('%d %b %Y %H:%M IST')}  ({wait/3600:.1f}h away)")

        time.sleep(wait)
        run_screener()


