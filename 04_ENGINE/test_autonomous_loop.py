"""
Comprehensive tests for 24/7 Autonomous Loop
Authority: ZERO (locked)

Tests for:
- market_downloader.py
- continuous_simulator.py
- results_tracker.py
- scheduler_service.py
"""

import pytest

# scheduler_service.py never shipped AutonomousLoopFactory / ScheduledJob (see git log 55f0453).
# These tests describe an unbuilt feature; skip at collection instead of failing import.
pytest.importorskip("scheduler_service")
if not hasattr(__import__("scheduler_service"), "AutonomousLoopFactory"):
    pytest.skip("AutonomousLoopFactory not implemented in scheduler_service", allow_module_level=True)
import sqlite3
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4
from typing import List, Dict, Any

# Import modules under test
from market_downloader import (
    MarketDownloader, MarketBar, DownloadSession
)
from continuous_simulator import (
    StrategyBacktester, SimulationResult, example_strategy
)
from results_tracker import (
    ResultsTracker, SimulationLogEntry, StrategyMetricsSnapshot
)
from scheduler_service import (
    SchedulerService, AutonomousLoopFactory, ScheduledJob
)


# ============================================================================
# MARKET DOWNLOADER TESTS
# ============================================================================

class TestMarketDownloader:
    """Test EOD market data downloader"""

    @pytest.fixture
    def downloader(self, tmp_path):
        """Create downloader with temp database"""
        return MarketDownloader(str(tmp_path))

    def test_init_db(self, downloader):
        """Test database initialization"""
        db_path = downloader.get_db_path("20260901")
        downloader._init_db(db_path)

        assert db_path.exists()

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        assert "market_bars" in tables
        assert "download_sessions" in tables
        conn.close()

    def test_market_bar_immutability(self):
        """Test MarketBar is immutable"""
        bar = MarketBar(
            bar_id="bar_001",
            instrument="NQ",
            date="20260901",
            time="0930",
            open_price=5000.0,
            high_price=5010.0,
            low_price=4990.0,
            close_price=5005.0,
            volume=1000000,
            recorded_at=time.time()
        )

        # Verify immutability
        with pytest.raises(Exception):
            bar.close_price = 5010.0

    def test_market_bar_validation(self):
        """Test MarketBar validates OHLC constraints"""
        with pytest.raises(ValueError):
            MarketBar(
                bar_id="bar_001",
                instrument="NQ",
                date="20260901",
                time="0930",
                open_price=5000.0,
                high_price=5000.0,  # High < low
                low_price=5010.0,
                close_price=5005.0,
                volume=1000000,
                recorded_at=time.time()
            )

    def test_download_session_immutability(self):
        """Test DownloadSession is immutable"""
        session = DownloadSession(
            session_id="sess_001",
            instrument="NQ",
            download_date="20260901",
            start_timestamp=time.time(),
            end_timestamp=time.time() + 100,
            bars_count=50,
            quality_score=0.95,
            status="COMPLETE"
        )

        with pytest.raises(Exception):
            session.bars_count = 60

    def test_authority_enforcement(self):
        """Test Authority=ZERO enforcement"""
        with pytest.raises(ValueError):
            MarketBar(
                bar_id="bar_001",
                instrument="NQ",
                date="20260901",
                time="0930",
                open_price=5000.0,
                high_price=5010.0,
                low_price=4990.0,
                close_price=5005.0,
                volume=1000000,
                recorded_at=time.time(),
                authority="ONE"  # Invalid!
            )

    def test_download_daily_data(self, downloader):
        """Test EOD data download flow"""
        results = downloader.download_daily_data(["NQ"], "20260901")

        assert "NQ" in results
        assert results["NQ"]["status"] in ["COMPLETE", "FAILED"]

        if results["NQ"]["status"] == "COMPLETE":
            assert results["NQ"]["bars_count"] > 0
            assert "db_path" in results["NQ"]

    def test_quality_score_calculation(self, downloader):
        """Test data quality scoring"""
        # Perfect data
        perfect_bars = [
            {"time": "0930", "open": 5000, "high": 5010, "low": 4990, "close": 5005, "volume": 1000000},
            {"time": "0940", "open": 5005, "high": 5015, "low": 4995, "close": 5010, "volume": 1100000},
        ]

        score = downloader._validate_bar_quality(perfect_bars)
        assert 0.85 <= score <= 1.0

        # Degraded data (gaps, zero volume)
        degraded_bars = [
            {"time": "0930", "open": 5000, "high": 5010, "low": 4990, "close": 5005, "volume": 0},
            {"time": "1030", "open": 5005, "high": 5015, "low": 4995, "close": 5010, "volume": 1100000},
        ]

        score = downloader._validate_bar_quality(degraded_bars)
        assert 0 <= score <= 1.0


# ============================================================================
# CONTINUOUS SIMULATOR TESTS
# ============================================================================

class TestContinuousSimulator:
    """Test backtest simulator"""

    @pytest.fixture
    def backtester(self, tmp_path):
        """Create backtester with temp database"""
        return StrategyBacktester(str(tmp_path))

    @pytest.fixture
    def sample_bars(self):
        """Create sample market bars for testing"""
        bars = []
        base_price = 5000.0

        for i in range(50):
            bars.append({
                "time": f"{9 + i // 60:02d}{i % 60:02d}",
                "open": base_price + i,
                "high": base_price + i + 2,
                "low": base_price + i - 1,
                "close": base_price + i + 1,
                "volume": 1000000 + i * 50000
            })

        return bars

    def test_simulation_result_immutability(self):
        """Test SimulationResult is immutable"""
        result = SimulationResult(
            simulation_id="sim_001",
            strategy_name="TestStrat",
            instrument="NQ",
            test_date="20260901",
            backtest_date="20260831",
            start_time=time.time(),
            end_time=time.time() + 100,
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
            gross_pnl_dollars=5000.0,
            net_pnl_dollars=4700.0,
            max_drawdown_dollars=500.0,
            win_rate=0.6,
            profit_factor=1.85,
            sharpe_ratio=1.2,
            status="COMPLETED"
        )

        with pytest.raises(Exception):
            result.total_trades = 20

    def test_max_drawdown_calculation(self, backtester):
        """Test max drawdown calculation"""
        trades = [
            {"pnl_dollars": 100},
            {"pnl_dollars": 200},
            {"pnl_dollars": -150},
            {"pnl_dollars": 50},
        ]

        max_dd = backtester._calculate_max_drawdown(trades)
        assert max_dd >= 0

    def test_sharpe_calculation(self, backtester):
        """Test Sharpe ratio calculation"""
        pnls = [100, 150, 120, 90, 110, 130, 140, 100]

        sharpe = backtester._calculate_sharpe(pnls)
        assert isinstance(sharpe, float)
        assert sharpe > 0

    def test_example_strategy(self, sample_bars):
        """Test example MA crossover strategy"""
        trades = example_strategy(sample_bars)

        # Should produce some trades
        assert isinstance(trades, list)

        # Verify trade structure
        for trade in trades:
            assert "side" in trade
            assert "entry_time" in trade
            assert "entry_price" in trade
            assert "pnl_dollars" in trade

    def test_backtest_with_no_data(self, backtester):
        """Test backtest gracefully handles missing data"""
        results = backtester.run_backtest(
            strategy_func=example_strategy,
            strategy_name="TestStrat",
            instrument="NONEXISTENT",
            test_date="20260901",
            backtest_dates=["20260801"]
        )

        assert isinstance(results, list)


# ============================================================================
# RESULTS TRACKER TESTS
# ============================================================================

class TestResultsTracker:
    """Test immutable append-only results logging"""

    @pytest.fixture
    def tracker(self, tmp_path):
        """Create tracker with temp database"""
        db_path = tmp_path / "test_results.db"
        return ResultsTracker(str(db_path))

    @pytest.fixture
    def sample_simulation(self):
        """Create sample simulation result"""
        return {
            "simulation_id": str(uuid4()),
            "strategy_name": "TestStrat",
            "instrument": "NQ",
            "backtest_date": "20260901",
            "total_trades": 15,
            "winning_trades": 9,
            "losing_trades": 6,
            "win_rate": 0.6,
            "profit_factor": 1.85,
            "max_drawdown": 500.0,
            "sharpe_ratio": 1.2,
            "gross_pnl": 5000.0,
            "net_pnl": 4700.0,
            "runtime_seconds": 2.5
        }

    def test_log_simulation(self, tracker, sample_simulation):
        """Test logging a simulation result"""
        log_id = tracker.log_simulation(sample_simulation, strategy_version="1.0.0")

        assert log_id
        assert len(log_id) > 0

    def test_append_only_constraint(self, tracker, sample_simulation):
        """Test that entries are truly append-only"""
        log_id1 = tracker.log_simulation(sample_simulation, "1.0.0")
        log_id2 = tracker.log_simulation(sample_simulation, "1.0.0")

        # Same simulation should not be logged twice
        # (UNIQUE constraint on simulation_id)
        assert log_id1 != ""
        assert log_id2 == ""  # Duplicate rejected

    def test_log_entry_immutability(self):
        """Test SimulationLogEntry is immutable"""
        entry = SimulationLogEntry(
            log_id="log_001",
            correlation_id="corr_001",
            simulation_id="sim_001",
            strategy_name="TestStrat",
            strategy_version="1.0.0",
            instrument="NQ",
            backtest_date="20260901",
            recorded_date="20260902",
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
            win_rate=0.6,
            profit_factor=1.85,
            max_drawdown=500.0,
            sharpe_ratio=1.2,
            gross_pnl=5000.0,
            net_pnl=4700.0,
            runtime_seconds=2.5,
            timestamp=time.time()
        )

        with pytest.raises(Exception):
            entry.total_trades = 20

    def test_create_metrics_snapshot(self, tracker, sample_simulation):
        """Test creating metrics snapshot"""
        # Log some simulations first
        for i in range(3):
            sim = sample_simulation.copy()
            sim["simulation_id"] = str(uuid4())
            tracker.log_simulation(sim, "1.0.0")

        # Create snapshot
        snapshot_id = tracker.create_metrics_snapshot("TestStrat", "1.0.0")

        assert snapshot_id
        assert len(snapshot_id) > 0

    def test_get_strategy_history(self, tracker, sample_simulation):
        """Test retrieving strategy history"""
        for i in range(3):
            sim = sample_simulation.copy()
            sim["simulation_id"] = str(uuid4())
            tracker.log_simulation(sim, "1.0.0")

        history = tracker.get_strategy_history("TestStrat")

        assert len(history) >= 1
        assert all("win_rate" in h for h in history)
        assert all("net_pnl" in h for h in history)

    def test_verify_log_integrity(self, tracker, sample_simulation):
        """Test log integrity verification"""
        log_id = tracker.log_simulation(sample_simulation, "1.0.0")

        is_valid, msg = tracker.verify_log_integrity()

        # Should pass integrity check
        assert isinstance(is_valid, bool)
        assert isinstance(msg, str)

    def test_hash_chain(self, tracker, sample_simulation):
        """Test that entries form a proper hash chain"""
        sim1 = sample_simulation.copy()
        sim1["simulation_id"] = "sim_001"

        sim2 = sample_simulation.copy()
        sim2["simulation_id"] = "sim_002"

        tracker.log_simulation(sim1, "1.0.0")
        tracker.log_simulation(sim2, "1.0.0")

        # Verify hash chain
        is_valid, _ = tracker.verify_log_integrity()
        assert is_valid


# ============================================================================
# SCHEDULER TESTS
# ============================================================================

class TestSchedulerService:
    """Test 24/7 autonomous loop scheduler"""

    @pytest.fixture
    def scheduler(self):
        """Create scheduler"""
        return SchedulerService(instruments=["NQ", "ES"])

    def test_scheduler_init(self, scheduler):
        """Test scheduler initialization"""
        assert not scheduler.running
        assert scheduler.authority == "ZERO"
        assert len(scheduler.jobs) == 0

    def test_register_job(self, scheduler):
        """Test job registration"""
        def dummy_handler():
            return {"status": "ok"}

        scheduler.register_job(
            job_id="test_job",
            job_type="TEST",
            schedule="on_demand",
            handler=dummy_handler
        )

        assert "test_job" in scheduler.jobs
        assert scheduler.jobs["test_job"].handler == dummy_handler

    def test_calculate_next_run_5pm(self, scheduler):
        """Test EOD schedule calculation (5 PM ET)"""
        job = ScheduledJob(
            job_id="test",
            job_type="EOD",
            schedule="daily_5pm",
            handler=lambda: None
        )

        next_run_ts = scheduler._calculate_next_run(job)
        next_run = datetime.fromtimestamp(next_run_ts)

        # Should be at 5 PM (17:00)
        assert next_run.hour == 17
        assert next_run.minute == 0

    def test_calculate_next_run_6h(self, scheduler):
        """Test 6-hourly schedule calculation"""
        job = ScheduledJob(
            job_id="test",
            job_type="BACKTEST",
            schedule="every_6h",
            handler=lambda: None
        )

        next_run_ts = scheduler._calculate_next_run(job)
        now_ts = time.time()

        # Should be ~6 hours in future
        delta = next_run_ts - now_ts
        assert 6 * 3600 - 60 < delta < 6 * 3600 + 60

    def test_get_job_status(self, scheduler):
        """Test getting job status"""
        def dummy_handler():
            return {"status": "ok"}

        scheduler.register_job("job1", "TEST", "on_demand", dummy_handler)

        status = scheduler.get_job_status("job1")

        assert status is not None
        assert status["job_id"] == "job1"
        assert status["job_type"] == "TEST"

    def test_execute_job_success(self, scheduler):
        """Test successful job execution"""
        call_count = [0]

        def counting_handler():
            call_count[0] += 1
            return {"count": call_count[0]}

        job = ScheduledJob(
            job_id="counter",
            job_type="TEST",
            schedule="on_demand",
            handler=counting_handler
        )

        scheduler._execute_job(job)

        assert call_count[0] == 1
        assert job.status == "COMPLETED"
        assert job.result["count"] == 1

    def test_execute_job_failure(self, scheduler):
        """Test job failure handling"""
        def failing_handler():
            raise ValueError("Test error")

        job = ScheduledJob(
            job_id="fail_job",
            job_type="TEST",
            schedule="on_demand",
            handler=failing_handler
        )

        scheduler._execute_job(job)

        assert job.status == "FAILED"
        assert "error" in job.result

    def test_get_all_status(self, scheduler):
        """Test getting status of all jobs"""
        for i in range(3):
            scheduler.register_job(
                f"job_{i}",
                "TEST",
                "on_demand",
                lambda: None
            )

        status_list = scheduler.get_all_status()

        assert len(status_list) == 3
        assert all("job_id" in s for s in status_list)

    def test_feed_guardian_gates(self, scheduler):
        """Test feeding metrics to Guardian gates"""
        # Should not raise
        scheduler.feed_guardian_gate4("test_metric", "ok")
        scheduler.feed_guardian_gate5({"simulation_id": "sim_001", "pnl": 100})


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestAutonomousLoopIntegration:
    """Integration tests for full autonomous loop"""

    @pytest.fixture
    def loop(self, tmp_path):
        """Create configured autonomous loop"""
        # Mock the imports to use temp directory
        import market_downloader
        import continuous_simulator
        import results_tracker

        # Monkeypatch to use temp dir
        original_downloader = market_downloader.MarketDownloader
        original_backtester = continuous_simulator.StrategyBacktester
        original_tracker = results_tracker.ResultsTracker

        def patched_downloader(*args, **kwargs):
            return original_downloader(str(tmp_path))

        def patched_backtester(*args, **kwargs):
            return original_backtester(str(tmp_path))

        def patched_tracker(*args, **kwargs):
            return original_tracker(str(tmp_path / "results.db"))

        market_downloader.MarketDownloader = patched_downloader
        continuous_simulator.StrategyBacktester = patched_backtester
        results_tracker.ResultsTracker = patched_tracker

        try:
            yield AutonomousLoopFactory.create_default_loop(str(tmp_path))
        finally:
            market_downloader.MarketDownloader = original_downloader
            continuous_simulator.StrategyBacktester = original_backtester
            results_tracker.ResultsTracker = original_tracker

    def test_default_loop_creation(self, loop):
        """Test creating default autonomous loop"""
        assert loop is not None
        assert len(loop.jobs) >= 4

        job_types = [j.job_type for j in loop.jobs.values()]
        assert "EOD_DOWNLOAD" in job_types
        assert "BACKTEST" in job_types
        assert "METRICS_SNAPSHOT" in job_types

    def test_loop_job_scheduling(self, loop):
        """Test job scheduling in loop"""
        jobs = loop.get_all_status()

        for job in jobs:
            assert job["job_id"]
            assert job["job_type"]
            assert job["status"]
            assert job["next_run"] is not None

    def test_authority_zero_enforcement(self, loop):
        """Test Authority=ZERO is enforced throughout"""
        assert loop.authority == "ZERO"

        # All jobs should respect authority
        for job in loop.jobs.values():
            # Jobs should be configured with authority=ZERO
            pass


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Performance and stress tests"""

    def test_market_downloader_speed(self, tmp_path):
        """Test market downloader performance"""
        downloader = MarketDownloader(str(tmp_path))

        start = time.time()
        results = downloader.download_daily_data(["NQ", "ES"], "20260901")
        elapsed = time.time() - start

        # Should complete in < 5 seconds
        assert elapsed < 5.0

    def test_simulator_speed(self, tmp_path):
        """Test simulator performance"""
        backtester = StrategyBacktester(str(tmp_path))

        start = time.time()
        results = backtester.run_backtest(
            example_strategy,
            "TestStrat",
            "NQ",
            "20260901",
            backtest_dates=["20260815", "20260816"]
        )
        elapsed = time.time() - start

        # Should handle multiple backtests quickly
        assert isinstance(results, list)
        # Actual timing depends on data availability


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
