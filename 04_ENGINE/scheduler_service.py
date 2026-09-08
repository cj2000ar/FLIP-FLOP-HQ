#!/usr/bin/env python3
"""24/7 Autonomous Scheduler Service"""

import logging
import time
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

try:
    from market_downloader import MarketDownloader, download_eod_job
    from health_check import HealthChecker
except ImportError as e:
    logger.error(f"Import failed: {e}")
    sys.exit(1)


class SchedulerService:
    def __init__(self, db_dir: str = "databases"):
        self.db_dir = Path(db_dir)
        self.db_dir.mkdir(exist_ok=True)
        self.downloader = MarketDownloader()
        self.health_checker = HealthChecker(str(self.db_dir))
        self.running = True
        logger.info("SchedulerService initialized")

    def run_loop(self, check_interval: int = 60) -> None:
        logger.info("Starting scheduler loop")
        logger.info("Authority: ZERO | Live: OFF")

        while self.running:
            try:
                now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"[{now}] Scheduler tick")

                # Health check
                health = self.health_checker.check_all()
                if health['status'] != 'HEALTHY':
                    logger.warning(f"Health: {health['status']}")

                # EOD download (after market close 16:00 UTC)
                if datetime.utcnow().hour == 16 and datetime.utcnow().minute < 5:
                    logger.info("Running EOD download...")
                    try:
                        self.downloader.download()
                    except Exception as e:
                        logger.error(f"EOD failed: {e}")

                time.sleep(check_interval)

            except KeyboardInterrupt:
                logger.info("Scheduler interrupted")
                self.running = False
            except Exception as e:
                logger.error(f"Error: {e}")
                time.sleep(check_interval)


def main():
    logger.info("FlipFlop HQ 24/7 Autonomous Scheduler")
    db_dir = os.getenv('FLIPFLOP_DB_DIR', 'databases')

    try:
        service = SchedulerService(db_dir)
        service.run_loop(check_interval=60)
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
