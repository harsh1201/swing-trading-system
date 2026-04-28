import time
import subprocess
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

if __name__ == "__main__":
    last_run_date = None
    logging.info("Swing Trading System Scheduler started.")
    logging.info("Waiting for 18:00 UTC (11:30 PM IST) daily to run screener...")

    while True:
        try:
            now = datetime.now(timezone.utc)
            current_date = now.date()
            
            # Run at 18:00 UTC once per day
            if now.hour >= 18 and current_date != last_run_date:
                run_screener()
                last_run_date = current_date
            
            # Sleep for 60 seconds
            time.sleep(60)
        except Exception as e:
            logging.error(f"Error in scheduler loop: {e}")
            time.sleep(60)
