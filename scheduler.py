import time
import subprocess
import logging
from datetime import datetime, timezone, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# IST = UTC+5:30
IST = timezone(timedelta(hours=5, minutes=30))

# Target run time: 11:30 IST, Monday(0) to Saturday(5)
RUN_HOUR   = 11
RUN_MINUTE = 30
RUN_DAYS   = {0, 1, 2, 3, 4, 5}  # Mon=0 ... Sat=5, Sun=6 excluded


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
    """Return seconds until the next 11:30 IST on a Mon-Sat."""
    now = datetime.now(IST)
    target = now.replace(hour=RUN_HOUR, minute=RUN_MINUTE, second=0, microsecond=0)

    # If today is a run day and we haven't passed 11:30 yet, run today
    if now.weekday() in RUN_DAYS and now < target:
        return (target - now).total_seconds()

    # Otherwise find the next valid day
    days_ahead = 1
    while days_ahead <= 7:
        candidate = target + timedelta(days=days_ahead)
        if candidate.weekday() in RUN_DAYS:
            return (candidate - now).total_seconds()
        days_ahead += 1

    return 24 * 3600  # fallback: 24 hours


if __name__ == "__main__":
    logging.info("Swing Trading System scheduler starting...")

    while True:
        wait = seconds_until_next_run()
        next_run = datetime.now(IST) + timedelta(seconds=wait)
        logging.info(f"Next run scheduled at: {next_run.strftime('%d %b %Y %H:%M IST')} ({wait/3600:.1f}h away)")

        time.sleep(wait)

        now = datetime.now(IST)
        if now.weekday() in RUN_DAYS:
            run_screener()
        else:
            logging.info("Not a trading day — skipping.")

