"""Standalone scheduler process: runs the daily scan every day at 8 AM
and can be extended with more cron-style jobs. Run with:
    python -m app.workers.scheduler
"""
import logging
import time

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from app.workers.jobs import run_daily_scan

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("ownly.scheduler")


def main():
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(run_daily_scan, CronTrigger(hour=8, minute=0), id="daily_scan")
    # Also run shortly after startup so a fresh deployment catches up
    scheduler.add_job(run_daily_scan, "date", run_date=None)
    logger.info("OWNLY scheduler started (daily scan at 08:00 UTC)")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    main()