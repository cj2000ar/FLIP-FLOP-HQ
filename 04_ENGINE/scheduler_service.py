"""
Scheduler Service - 24/7 Autonomous Loop Orchestrator
Authority: ZERO (locked, non-negotiable)

Cron-like scheduling:
- 5 PM ET: trigger EOD download
- 6-hourly: trigger full backtest
- Continuous: monitor health, feed Guardian Gates
- Authority-ZERO: evidence-scoped, no live trading
"""

import os
import time
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
from uuid import uuid4
import threading

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class ScheduledJob:
    """Job definition for scheduler"""
    job_id: str
    job_type: str  # "EOD_DOWNLOAD" | "BACKTEST" | "METRICS_SNAPSHOT"
    schedule: str  # "daily_5pm" | "every_6h" | "on_demand"
    handler: Callable
    enabled: bool = True
    last_run: Optional[float] = None
    next_run: Optional[float] = None
    status: str = JobStatus.PENDING
    result: Optional[Dict[str, Any]] = None


class SchedulerService:
    """24/7 autonomous loop orchestrator"""

    def __init__(self, instruments: List[str] = None):
        self.instruments = instruments or ["NQ", "ES", "MNQ", "MES"]
        self.jobs: Dict[str, ScheduledJob] = {}
        self.running = False
        self.lock = threading.Lock()
        self.authority = "ZERO"

    def register_job(self, job_id: str, job_type: str, schedule: str,
                    handler: Callable, enabled: bool = True) -> None:
        """Register a scheduled job"""
        job = ScheduledJob(
            job_id=job_id,
            job_type=job_type,
            schedule=schedule,
            handler=handler,
            enabled=enabled
        )

        # Calculate first run
        job.next_run = self._calculate_next_run(job)

        with self.lock:
            self.jobs[job_id] = job

        logger.info(f"Registered job {job_id}: {job_type} ({schedule})")

    def _calculate_next_run(self, job: ScheduledJob) -> float:
        """Calculate next run time for job"""
        now = datetime.now()

        if job.schedule == "daily_5pm":
            # 5 PM ET (17:00 EST)
            next_run = now.replace(hour=17, minute=0, second=0, microsecond=0)

            # If we're already past 5 PM, schedule for tomorrow
            if now > next_run:
                next_run += timedelta(days=1)

            return next_run.timestamp()

        elif job.schedule == "every_6h":
            # Every 6 hours
            return (now + timedelta(hours=6)).timestamp()

        elif job.schedule == "on_demand":
            # Run immediately
            return now.timestamp()

        return now.timestamp()

    def start(self) -> None:
        """Start the scheduler (blocking)"""
        self.running = True
        logger.info("Scheduler started - Authority: ZERO")

        try:
            while self.running:
                self._check_and_run_jobs()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Scheduler interrupted")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the scheduler"""
        self.running = False
        logger.info("Scheduler stopped")

    def start_background(self) -> threading.Thread:
        """Start scheduler in background thread"""
        thread = threading.Thread(target=self.start, daemon=True)
        thread.start()
        logger.info("Scheduler started in background")
        return thread

    def _check_and_run_jobs(self) -> None:
        """Check if any jobs should run"""
        now = time.time()

        with self.lock:
            for job_id, job in self.jobs.items():
                if not job.enabled:
                    continue

                # Check if job should run
                if job.next_run and now >= job.next_run:
                    self._execute_job(job)

    def _execute_job(self, job: ScheduledJob) -> None:
        """Execute a job"""
        job.status = JobStatus.RUNNING
        job.last_run = time.time()

        logger.info(f"Executing job {job.job_id}: {job.job_type}")

        try:
            # Run job handler
            result = job.handler()

            job.status = JobStatus.COMPLETED
            job.result = result

            logger.info(f"Job {job.job_id} completed: {result}")

            # Recalculate next run
            job.next_run = self._calculate_next_run(job)

        except Exception as e:
            job.status = JobStatus.FAILED
            job.result = {"error": str(e)}

            logger.error(f"Job {job.job_id} failed: {str(e)}")

            # Reschedule on failure (after 30 minutes)
            job.next_run = (datetime.now() + timedelta(minutes=30)).timestamp()

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a job"""
        with self.lock:
            job = self.jobs.get(job_id)

        if not job:
            return None

        return {
            "job_id": job.job_id,
            "job_type": job.job_type,
            "status": job.status,
            "last_run": job.last_run,
            "next_run": job.next_run,
            "result": job.result
        }

    def get_all_status(self) -> List[Dict[str, Any]]:
        """Get status of all jobs"""
        with self.lock:
            jobs = list(self.jobs.values())

        return [
            {
                "job_id": job.job_id,
                "job_type": job.job_type,
                "status": job.status,
                "last_run": job.last_run,
                "next_run": job.next_run,
                "enabled": job.enabled
            }
            for job in jobs
        ]

    def feed_guardian_gate4(self, metric: str, value: Any) -> None:
        """Feed metrics to Guardian Gate 4 (machine health)"""
        # Gate 4: Verifies machine readiness
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "gate": "GATE_4_MACHINE_HEALTH",
            "metric": metric,
            "value": value,
            "authority": self.authority
        }

        logger.info(f"Guardian Gate 4: {metric}={value}")

    def feed_guardian_gate5(self, canary_result: Dict[str, Any]) -> None:
        """Feed canary results to Guardian Gate 5"""
        # Gate 5: Verifies canary (strategy performance)
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "gate": "GATE_5_CANARY",
            "simulation_results": canary_result,
            "authority": self.authority
        }

        logger.info(f"Guardian Gate 5: canary_pnl={canary_result.get('pnl', 0)}")


# ============================================================================
# AUTONOMOUS LOOP FACTORY
# ============================================================================

class AutonomousLoopFactory:
    """Create configured autonomous loop with all 4 components"""

    @staticmethod
    def create_default_loop(
        db_dir: str = "databases",
        strategy_func: Optional[Callable] = None
    ) -> SchedulerService:
        """
        Create default autonomous loop with:
        1. EOD download at 5 PM ET
        2. Backtest every 6 hours
        3. Metrics snapshots daily
        """
        from market_downloader import download_eod_job
        from continuous_simulator import StrategyBacktester, example_strategy
        from results_tracker import ResultsTracker

        scheduler = SchedulerService()
        tracker = ResultsTracker()
        backtester = StrategyBacktester(db_dir)

        if strategy_func is None:
            strategy_func = example_strategy

        # Job 1: EOD Download (5 PM ET)
        def eod_download_handler():
            return download_eod_job(scheduler.instruments)

        scheduler.register_job(
            job_id="eod_download",
            job_type="EOD_DOWNLOAD",
            schedule="daily_5pm",
            handler=eod_download_handler,
            enabled=True
        )

        # Job 2: Continuous Backtest (every 6 hours)
        def backtest_handler():
            today = datetime.now().strftime("%Y%m%d")
            results = []

            for instrument in scheduler.instruments:
                sim_results = backtester.run_backtest(
                    strategy_func=strategy_func,
                    strategy_name="AutoStrategy_v1",
                    instrument=instrument,
                    test_date=today,
                    backtest_dates=[today]
                )

                for sim in sim_results:
                    if sim['status'] == 'COMPLETED':
                        # Log to results tracker
                        result_dict = {
                            "simulation_id": sim['simulation_id'],
                            "strategy_name": "AutoStrategy_v1",
                            "instrument": instrument,
                            "backtest_date": today,
                            **sim.get('metrics', {})
                        }
                        log_id = tracker.log_simulation(result_dict, "1.0.0")

                        # Feed to Guardian Gate 5
                        scheduler.feed_guardian_gate5({
                            "simulation_id": sim['simulation_id'],
                            "pnl": sim.get('metrics', {}).get('net_pnl', 0),
                            "win_rate": sim.get('metrics', {}).get('win_rate', 0),
                            "timestamp": time.time()
                        })

                results.extend(sim_results)

            return {"total_backtests": len(results), "results": results}

        scheduler.register_job(
            job_id="continuous_backtest",
            job_type="BACKTEST",
            schedule="every_6h",
            handler=backtest_handler,
            enabled=True
        )

        # Job 3: Metrics Snapshots (daily)
        def metrics_snapshot_handler():
            snapshot_id = tracker.create_metrics_snapshot(
                "AutoStrategy_v1",
                "1.0.0",
                lookback_days=7
            )

            # Feed to Guardian Gate 4
            history = tracker.get_strategy_history("AutoStrategy_v1", days=7)
            if history:
                scheduler.feed_guardian_gate4(
                    "strategy_health",
                    {
                        "runs": len(history),
                        "avg_win_rate": sum(h['win_rate'] for h in history) / len(history),
                        "snapshot_id": snapshot_id
                    }
                )

            return {"snapshot_id": snapshot_id, "entries": len(history)}

        scheduler.register_job(
            job_id="metrics_snapshot",
            job_type="METRICS_SNAPSHOT",
            schedule="daily_5pm",
            handler=metrics_snapshot_handler,
            enabled=True
        )

        # Job 4: Log Integrity Check (every 24 hours)
        def integrity_check_handler():
            is_valid, msg = tracker.verify_log_integrity()

            if is_valid:
                scheduler.feed_guardian_gate4("log_integrity", "VERIFIED")
            else:
                logger.error(f"Log integrity check failed: {msg}")
                scheduler.feed_guardian_gate4("log_integrity", "FAILED")

            return {"valid": is_valid, "message": msg}

        scheduler.register_job(
            job_id="integrity_check",
            job_type="INTEGRITY_CHECK",
            schedule="every_6h",
            handler=integrity_check_handler,
            enabled=True
        )

        return scheduler


# ============================================================================
# CLI / ENTRY POINT
# ============================================================================

def main():
    """Run autonomous loop"""
    logger.info("Starting FlipFlop HQ 24/7 Autonomous Loop")
    logger.info("Authority: ZERO (locked, non-negotiable)")

    # Create loop
    loop = AutonomousLoopFactory.create_default_loop()

    # Print status
    logger.info("Registered jobs:")
    for status in loop.get_all_status():
        logger.info(f"  - {status['job_id']}: {status['job_type']} ({status['status']})")

    # Start scheduler (blocking)
    loop.start()


if __name__ == "__main__":
    main()
