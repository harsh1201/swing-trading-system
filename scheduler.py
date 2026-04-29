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
    logging.info("Swing Trading System starting up...")
    
    # Run immediately on startup (triggered by Fly.io restart)
    logging.info("Triggering screener run on startup...")
    run_screener()
    
    logging.info("Execution complete. System entering standby mode.")
    logging.info("To re-trigger, simply restart the deployment in Fly.io.")
    
    # Keep the process alive so Fly.io doesn't restart it immediately
    while True:
        time.sleep(3600)
