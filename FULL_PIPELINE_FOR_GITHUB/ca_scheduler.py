"""
ca_scheduler.py — Autonomous Scraper Daemon
===================================================
Runs indefinitely in the background, triggering the scraper for 
specific sources at the requested intervals:
- Monthly: VisionIAS, InsightsIAS
- Daily: ForumIAS, The Hindu, Indian Express
- 5-Days: PIB, Drishti IAS
"""

import time
import logging
import sys
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from ca_scraper import run_all_scrapers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | SCHEDULER | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/ca_scheduler.log", mode="a", encoding="utf-8"),
    ]
)
logger = logging.getLogger("ca_scheduler")

def job_monthly():
    logger.info("Triggering MONTHLY scrape (VisionIAS, InsightsIAS)")
    summary = run_all_scrapers(sources=["visionias", "insightsias"])
    logger.info(f"Monthly Scrape Complete: {summary}")

def job_daily():
    logger.info("Triggering DAILY scrape (ForumIAS, The Hindu, Indian Express)")
    summary = run_all_scrapers(sources=["forumias", "thehindu", "indianexpress"])
    logger.info(f"Daily Scrape Complete: {summary}")

def job_5_days():
    logger.info("Triggering 5-DAY scrape (PIB, Drishti IAS)")
    summary = run_all_scrapers(sources=["pib", "drishtiias"])
    logger.info(f"5-Day Scrape Complete: {summary}")

def main():
    logger.info("Starting Autonomous Current Affairs Scheduler...")
    scheduler = BlockingScheduler()

    # Schedule Monthly (Runs on the 1st of every month at 02:00 AM)
    scheduler.add_job(job_monthly, 'cron', day=1, hour=2, minute=0)

    # Schedule Daily (Runs every day at 03:00 AM)
    scheduler.add_job(job_daily, 'cron', hour=3, minute=0)

    # Schedule Every 5 Days (Runs at 04:00 AM)
    scheduler.add_job(job_5_days, 'interval', days=5, start_date=datetime.now().replace(hour=4, minute=0, second=0))

    try:
        logger.info("Scheduler is active. Press Ctrl+C to exit.")
        # Trigger an immediate run just for verification if needed (uncomment below)
        # job_daily() 
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")

if __name__ == "__main__":
    main()
